from __future__ import annotations

import csv
import io
from copy import deepcopy
from typing import Any


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or value is None or value == "":
        return None
    if isinstance(value, dict):
        value = value.get("amount") if "amount" in value else value.get("value")
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _dig(obj: dict[str, Any], *paths: str) -> Any:
    for path in paths:
        cur: Any = obj
        ok = True
        for part in path.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                ok = False
                break
        if ok and cur not in (None, ""):
            return cur
    return None


def _rows(payload: Any, keys: tuple[str, ...] = ("results", "data", "rows", "items")) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [dict(x) for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, list):
                return [dict(x) for x in value if isinstance(x, dict)]
        return [payload]
    return []


def _ratio(a: float | None, b: float | None, multiplier: float = 1.0) -> float | None:
    if a is None or b in (None, 0):
        return None
    return round((a / b) * multiplier, 4)


def _totals(rows: list[dict[str, Any]]) -> dict[str, Any]:
    sum_fields = ["impressions", "reach", "clicks", "spend", "conversions", "leads", "purchases", "revenue"]
    total = {k: round(sum((r.get(k) or 0) for r in rows), 6) for k in sum_fields}
    total["ctr"] = _ratio(total["clicks"], total["impressions"], 100)
    total["cpc"] = _ratio(total["spend"], total["clicks"])
    total["cpm"] = _ratio(total["spend"], total["impressions"], 1000)
    total["conversion_rate"] = _ratio(total["conversions"], total["clicks"], 100)
    total["cpa"] = _ratio(total["spend"], total["conversions"])
    total["roas"] = _ratio(total["revenue"], total["spend"])
    return total


def _envelope(request_id: str, provider: str, rows: list[dict[str, Any]], payload: Any, context: dict[str, Any]) -> dict[str, Any]:
    total = _totals(rows)
    target = context.get("target") or context.get("account_id") or "ad account"
    currency = context.get("currency")
    claim = (
        f"{provider} performance for {target}: spend={total['spend']:.2f}"
        + (f" {currency}" if currency else "")
        + f", impressions={int(total['impressions'])}, clicks={int(total['clicks'])}, "
          f"conversions={total['conversions']:.2f}, purchases={total['purchases']:.2f}."
    )
    return {
        "request_id": request_id,
        "provider": provider,
        "capability": "ads.performance.read",
        "degraded": False,
        "status": "ok",
        "data": {"context": context, "rows": rows, "totals": total, "raw": payload},
        "evidence": [{
            "kind": "fact",
            "claim": claim,
            "source_ref": context.get("source_ref") or f"provider://{provider}/performance/{target}",
            "source_title": f"{provider} performance report",
            "confidence": 0.99,
            "notes": "Derived CTR/CPC/CPM/CPA/ROAS are calculated from the normalized returned report rows.",
        }],
        "state_patch": {},
    }


def normalize_google_ads_result(*, request_id: str, payload: Any, context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = dict(context or {})
    out = []
    for r in _rows(payload):
        spend_micros = _num(_dig(r, "metrics.cost_micros", "cost_micros"))
        out.append({
            "entity_id": _dig(r, "campaign.id", "campaign_id"),
            "entity_name": _dig(r, "campaign.name", "campaign_name"),
            "status": _dig(r, "campaign.status", "status"),
            "impressions": _num(_dig(r, "metrics.impressions", "impressions")) or 0,
            "reach": _num(_dig(r, "metrics.unique_users", "reach")) or 0,
            "clicks": _num(_dig(r, "metrics.clicks", "clicks")) or 0,
            "spend": (spend_micros / 1_000_000) if spend_micros is not None else 0,
            "conversions": _num(_dig(r, "metrics.conversions", "conversions")) or 0,
            "leads": _num(_dig(r, "metrics.all_conversions_from_interactions_rate", "leads")) or 0,
            "purchases": _num(_dig(r, "purchases")) or 0,
            "revenue": _num(_dig(r, "metrics.conversions_value", "revenue")) or 0,
            "raw": deepcopy(r),
        })
    return _envelope(request_id, "google_ads", out, payload, context)


def _meta_action(actions: Any, names: set[str]) -> float:
    total = 0.0
    if isinstance(actions, list):
        for item in actions:
            if not isinstance(item, dict):
                continue
            if str(item.get("action_type")) in names:
                total += _num(item.get("value")) or 0
    return total


def normalize_meta_ads_result(*, request_id: str, payload: Any, context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = dict(context or {})
    out = []
    for r in _rows(payload):
        actions = r.get("actions")
        values = r.get("action_values")
        purchases = _meta_action(actions, {"purchase", "offsite_conversion.fb_pixel_purchase", "omni_purchase"})
        leads = _meta_action(actions, {"lead", "onsite_conversion.lead_grouped", "offsite_conversion.fb_pixel_lead"})
        conversions = _meta_action(actions, {"purchase", "offsite_conversion.fb_pixel_purchase", "omni_purchase", "lead", "offsite_conversion.fb_pixel_lead"})
        revenue = _meta_action(values, {"purchase", "offsite_conversion.fb_pixel_purchase", "omni_purchase"})
        out.append({
            "entity_id": r.get("campaign_id") or r.get("adset_id") or r.get("ad_id"),
            "entity_name": r.get("campaign_name") or r.get("adset_name") or r.get("ad_name"),
            "status": r.get("effective_status") or r.get("status"),
            "impressions": _num(r.get("impressions")) or 0,
            "reach": _num(r.get("reach")) or 0,
            "clicks": _num(r.get("clicks") or r.get("inline_link_clicks")) or 0,
            "spend": _num(r.get("spend")) or 0,
            "conversions": conversions,
            "leads": leads,
            "purchases": purchases,
            "revenue": revenue,
            "raw": deepcopy(r),
        })
    return _envelope(request_id, "meta_ads", out, payload, context)


def _parse_yandex_tsv(text: str) -> list[dict[str, Any]]:
    lines = [line for line in text.splitlines() if line.strip()]
    while lines and ("	" not in lines[0] or lines[0].startswith("ReportName")):
        lines.pop(0)
    if not lines:
        return []
    return [dict(x) for x in csv.DictReader(io.StringIO("
".join(lines)), delimiter="	")]


def normalize_yandex_direct_result(*, request_id: str, payload: Any, context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = dict(context or {})
    rows = _parse_yandex_tsv(payload) if isinstance(payload, str) else _rows(payload)
    out = []
    for r in rows:
        out.append({
            "entity_id": r.get("CampaignId") or r.get("AdGroupId") or r.get("AdId"),
            "entity_name": r.get("CampaignName") or r.get("AdGroupName"),
            "status": r.get("Status"),
            "impressions": _num(r.get("Impressions")) or 0,
            "reach": _num(r.get("Reach")) or 0,
            "clicks": _num(r.get("Clicks")) or 0,
            "spend": _num(r.get("Cost")) or 0,
            "conversions": _num(r.get("Conversions") or r.get("ConversionsAnyGoal")) or 0,
            "leads": _num(r.get("Leads")) or 0,
            "purchases": _num(r.get("Purchases")) or 0,
            "revenue": _num(r.get("Revenue")) or 0,
            "raw": deepcopy(r),
        })
    return _envelope(request_id, "yandex_direct", out, payload, context)


def normalize_apple_ads_result(*, request_id: str, payload: Any, context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = dict(context or {})
    rows = _rows(payload, ("data", "rows", "results", "items"))
    out = []
    for r in rows:
        metrics = r.get("metrics") if isinstance(r.get("metrics"), dict) else r
        spend = _dig(metrics, "spend.amount", "localSpend.amount", "spend", "localSpend")
        installs = _num(_dig(metrics, "installs", "totalInstalls", "tapInstalls")) or 0
        out.append({
            "entity_id": _dig(r, "metadata.campaignId", "campaignId", "id"),
            "entity_name": _dig(r, "metadata.campaignName", "campaignName", "name"),
            "status": _dig(r, "metadata.status", "status"),
            "impressions": _num(_dig(metrics, "impressions")) or 0,
            "reach": _num(_dig(metrics, "reach")) or 0,
            "clicks": _num(_dig(metrics, "taps", "clicks")) or 0,
            "spend": _num(spend) or 0,
            "conversions": installs,
            "leads": 0,
            "purchases": _num(_dig(metrics, "purchases")) or 0,
            "revenue": _num(_dig(metrics, "revenue.amount", "revenue")) or 0,
            "raw": deepcopy(r),
        })
    return _envelope(request_id, "apple_ads", out, payload, context)


NORMALIZERS = {
    "google_ads": normalize_google_ads_result,
    "meta_ads": normalize_meta_ads_result,
    "yandex_direct": normalize_yandex_direct_result,
    "apple_ads": normalize_apple_ads_result,
}


def normalize_ads_result(*, provider: str, request_id: str, payload: Any, context: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        fn = NORMALIZERS[provider]
    except KeyError as exc:
        raise ValueError(f"Unsupported ads provider: {provider}") from exc
    return fn(request_id=request_id, payload=payload, context=context)
