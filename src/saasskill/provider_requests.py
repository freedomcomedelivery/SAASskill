from __future__ import annotations

from datetime import date
from typing import Any


def build_direct_read_spec(
    *,
    provider: str,
    capability: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Build a provider-specific read spec from a logical capability.

    Raises with a precise missing-input message rather than inventing query/target
    parameters.
    """
    ctx = dict(context or {})
    target = ctx.get("target") or ctx.get("domain") or ctx.get("product_domain")
    query = ctx.get("query") or ctx.get("keyword") or ctx.get("phrase")
    country = str(ctx.get("country") or ctx.get("database") or "us").lower()
    limit = int(ctx.get("limit") or 100)

    if provider == "ahrefs":
        if capability == "seo.keyword_metrics":
            if not query:
                raise ValueError("Ahrefs keyword metrics require context.query/keyword")
            return {
                "endpoint": "keywords-explorer/matching-terms",
                "params": {"keywords": query, "country": country, "limit": limit, "select": "keyword,volume,cpc,difficulty,intents,traffic_potential"},
                "context": ctx,
            }
        if not target:
            raise ValueError(f"Ahrefs {capability} requires context.target/domain")
        report_date = ctx.get("date") or date.today().isoformat()
        mapping = {
            "seo.domain_metrics": (
                "site-explorer/domain-rating",
                {"target": target, "date": report_date},
            ),
            "seo.competitor_traffic": (
                "site-explorer/organic-competitors",
                {
                    "target": target,
                    "country": country,
                    "date": report_date,
                    "limit": limit,
                    "select": "competitor_domain,competitor_url,domain_rating,keywords_common,keywords_competitor,keywords_target,share,traffic,value",
                },
            ),
            "seo.backlinks": (
                "site-explorer/refdomains",
                {
                    "target": target,
                    "limit": limit,
                    "select": "domain,domain_rating,links_to_target,traffic_domain,is_spam,first_seen,last_seen",
                },
            ),
            "seo.competitor_ads": (
                "site-explorer/paid-pages",
                {
                    "target": target,
                    "country": country,
                    "date": report_date,
                    "limit": limit,
                    "select": "url,ads_count,keywords,sum_traffic,value,top_keyword,top_keyword_volume",
                },
            ),
        }
        if capability not in mapping:
            raise ValueError(f"Unsupported Ahrefs capability: {capability}")
        endpoint, params = mapping[capability]
        return {"endpoint": endpoint, "params": {k: v for k, v in params.items() if v is not None}, "context": ctx}

    if provider == "semrush":
        if capability == "seo.keyword_metrics":
            if not query:
                raise ValueError("Semrush keyword metrics require context.query/keyword")
            # Legacy v3 phrase report kept for direct compatibility; official MCP/v4 is preferred.
            return {
                "report_type": "phrase_all",
                "params": {
                    "type": "phrase_all",
                    "phrase": query,
                    "database": country,
                    "display_limit": limit,
                    "export_columns": "Ph,Nq,Cp,Co,Kd",
                },
                "context": ctx,
            }
        if not target:
            raise ValueError(f"Semrush {capability} requires context.target/domain")
        mapping = {
            "seo.domain_metrics": ("domain_rank", {"type": "domain_rank", "domain": target, "database": country, "export_columns": "Dn,Rk,Or,Ot,Oc,Ad,At,Ac"}),
            "seo.competitor_traffic": ("domain_organic_organic", {"type": "domain_organic_organic", "domain": target, "database": country, "display_limit": limit}),
            "seo.backlinks": ("backlinks_overview", {"type": "backlinks_overview", "target": target, "target_type": "root_domain"}),
            "seo.competitor_ads": ("domain_adwords", {"type": "domain_adwords", "domain": target, "database": country, "display_limit": limit}),
        }
        if capability not in mapping:
            raise ValueError(f"Unsupported Semrush capability: {capability}")
        report_type, params = mapping[capability]
        return {"report_type": report_type, "params": params, "context": ctx}

    if provider == "ga4":
        if capability != "analytics.funnel.read":
            raise ValueError(f"Unsupported GA4 capability: {capability}")
        start = ctx.get("date_from") or ctx.get("start_date")
        end = ctx.get("date_to") or ctx.get("end_date")
        if not start or not end:
            raise ValueError("GA4 funnel read requires context.date_from/date_to")
        metrics = ctx.get("metrics") or ["sessions", "totalUsers", "conversions"]
        dimensions = ctx.get("dimensions") or []
        return {
            "property_id": ctx.get("property_id"),
            "dimensions": dimensions,
            "metrics": metrics,
            "date_ranges": [{"start_date": start, "end_date": end}],
            "limit": limit,
            "context": ctx,
        }

    if provider == "posthog":
        if capability != "analytics.funnel.read":
            raise ValueError(f"Unsupported PostHog capability: {capability}")
        body = ctx.get("query_body")
        if not body:
            events = ctx.get("events")
            if not events:
                raise ValueError("PostHog funnel read requires context.query_body or context.events")
            body = {
                "query": {
                    "kind": "FunnelsQuery",
                    "series": [{"kind": "EventsNode", "event": str(event)} for event in events],
                    "dateRange": {"date_from": ctx.get("date_from"), "date_to": ctx.get("date_to")},
                }
            }
        return {"body": body, "context": ctx}

    if provider == "yandex_metrica":
        if capability != "analytics.funnel.read":
            raise ValueError(f"Unsupported Yandex Metrica capability: {capability}")
        metrics = ctx.get("metrics") or "ym:s:visits,ym:s:users"
        params = {
            "date1": ctx.get("date_from"),
            "date2": ctx.get("date_to"),
            "metrics": metrics,
            "dimensions": ctx.get("dimensions"),
            "limit": limit,
        }
        return {"params": {k: v for k, v in params.items() if v is not None}, "context": ctx}

    if provider == "hubspot":
        if capability != "crm.leads.read":
            raise ValueError(f"Unsupported HubSpot capability: {capability}")
        object_type = ctx.get("object_type") or "contacts"
        if object_type not in {"contacts", "deals", "companies"}:
            raise ValueError("HubSpot object_type must be contacts, deals or companies")
        properties = ctx.get("properties") or (
            ["email", "lifecyclestage", "hs_lead_status"]
            if object_type == "contacts"
            else ["dealname", "dealstage", "amount", "closedate"]
        )
        return {
            "path": f"/crm/v3/objects/{object_type}",
            "params": {"limit": min(limit, 100), "properties": ",".join(properties)},
            "context": ctx,
        }

    if provider == "stripe":
        if capability != "payments.transactions.read":
            raise ValueError(f"Unsupported Stripe capability: {capability}")
        resource = ctx.get("resource") or "payment_intents"
        if resource not in {"payment_intents", "charges", "invoices"}:
            raise ValueError("Stripe resource must be payment_intents, charges or invoices")
        params: dict[str, Any] = {"limit": min(limit, 100)}
        if ctx.get("created_gte") is not None:
            params["created[gte]"] = ctx["created_gte"]
        if ctx.get("created_lte") is not None:
            params["created[lte]"] = ctx["created_lte"]
        return {"resource": resource, "params": params, "context": ctx}

    raise ValueError(f"No direct read spec builder for provider {provider}")
