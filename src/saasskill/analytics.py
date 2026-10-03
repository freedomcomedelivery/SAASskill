from __future__ import annotations

from typing import Any

NORMALIZED = ("reach", "visits", "clicks", "leads", "qualified_leads", "payments", "revenue")

DEFAULT_ALIASES = {
    "reach": ("reach", "users", "activeUsers", "totalUsers", "visitors", "unique_users"),
    "visits": ("visits", "sessions", "screenPageViews", "pageviews", "page_views"),
    "clicks": ("clicks", "link_clicks"),
    "leads": ("leads", "lead", "generate_lead", "form_submits"),
    "qualified_leads": ("qualified_leads", "qualified", "sqls", "mqls"),
    "payments": ("payments", "purchases", "purchase", "ecommercePurchases", "transactions"),
    "revenue": ("revenue", "totalRevenue", "purchaseRevenue", "gross_revenue"),
}


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _ga4_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    metric_headers = [h.get("name") for h in payload.get("metricHeaders", []) if isinstance(h, dict)]
    dimension_headers = [h.get("name") for h in payload.get("dimensionHeaders", []) if isinstance(h, dict)]
    out = []
    for row in payload.get("rows", []) or []:
        if not isinstance(row, dict):
            continue
        item: dict[str, Any] = {}
        for name, val in zip(dimension_headers, row.get("dimensionValues", []) or []):
            if name:
                item[name] = val.get("value") if isinstance(val, dict) else val
        for name, val in zip(metric_headers, row.get("metricValues", []) or []):
            if name:
                item[name] = val.get("value") if isinstance(val, dict) else val
        out.append(item)
    return out


def _metrica_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    query = payload.get("query") or {}
    metric_names = query.get("metrics") or []
    if isinstance(metric_names, str):
        metric_names = metric_names.split(",")
    out = []
    for row in payload.get("data", []) or []:
        if not isinstance(row, dict):
            continue
        item: dict[str, Any] = {}
        for name, value in zip(metric_names, row.get("metrics", []) or []):
            item[str(name)] = value
        out.append(item)
    return out


def _posthog_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [dict(x) for x in payload if isinstance(x, dict)]
    if not isinstance(payload, dict):
        return []
    columns = payload.get("columns")
    results = payload.get("results")
    if isinstance(columns, list) and isinstance(results, list):
        out = []
        for row in results:
            if isinstance(row, list):
                out.append({str(k): v for k, v in zip(columns, row)})
            elif isinstance(row, dict):
                out.append(dict(row))
        return out
    for key in ("data", "rows", "items", "result"):
        value = payload.get(key)
        if isinstance(value, list):
            return [dict(x) for x in value if isinstance(x, dict)]
    return [payload]


def _generic_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [dict(x) for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in ("data", "rows", "results", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [dict(x) for x in value if isinstance(x, dict)]
        return [payload]
    return []


def _aggregate(rows: list[dict[str, Any]], field_map: dict[str, list[str]] | None = None) -> dict[str, float | None]:
    aliases = {k: list(DEFAULT_ALIASES[k]) for k in NORMALIZED}
    for key, values in (field_map or {}).items():
        if key in aliases:
            aliases[key] = list(values) + aliases[key]
    totals: dict[str, float | None] = {}
    for logical in NORMALIZED:
        seen_any = False
        total = 0.0
        for row in rows:
            value = None
            for candidate in aliases[logical]:
                if candidate in row and row[candidate] not in (None, ""):
                    value = _num(row[candidate])
                    if value is not None:
                        break
            if value is not None:
                seen_any = True
                total += value
        totals[logical] = round(total, 6) if seen_any else None
    return totals


def normalize_analytics_result(*, provider: str, request_id: str, payload: Any, context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = dict(context or {})
    if provider == "ga4" and isinstance(payload, dict):
        rows = _ga4_rows(payload)
    elif provider == "yandex_metrica" and isinstance(payload, dict):
        rows = _metrica_rows(payload)
    elif provider == "posthog":
        rows = _posthog_rows(payload)
    elif provider == "analytics":
        rows = _generic_rows(payload)
    else:
        raise ValueError(f"Unsupported analytics provider: {provider}")

    totals = _aggregate(rows, context.get("field_map"))
    known = {k: v for k, v in totals.items() if v is not None}
    merge_patch = {}
    if context.get("workflow") == "existing_project_audit":
        merge_patch = {
            "audit_snapshot": {
                "analytics": {"configured": True, "provider": provider},
                "funnel": known,
            }
        }

    return {
        "request_id": request_id,
        "provider": provider,
        "capability": "analytics.funnel.read",
        "degraded": False,
        "status": "ok",
        "data": {"context": context, "rows": rows, "totals": totals, "raw": payload},
        "evidence": [{
            "kind": "fact",
            "claim": f"{provider} returned {len(rows)} analytics rows; normalized observed funnel metrics: {known}.",
            "source_ref": context.get("source_ref") or f"provider://{provider}/funnel",
            "source_title": f"{provider} analytics funnel",
            "confidence": 0.98,
            "notes": "Missing normalized steps remain null rather than inferred.",
        }],
        "state_patch": {},
        "state_merge_patch": merge_patch,
    }
