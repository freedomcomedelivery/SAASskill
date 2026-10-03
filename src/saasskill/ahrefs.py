from __future__ import annotations

from statistics import median
from typing import Any

ENDPOINT_CAPABILITY = {
    "keywords-explorer/matching-terms": "seo.keyword_metrics",
    "keywords-explorer/overview": "seo.keyword_metrics",
    "site-explorer/domain-rating": "seo.domain_metrics",
    "site-explorer/metrics": "seo.domain_metrics",
    "site-explorer/organic-competitors": "seo.competitor_traffic",
    "site-explorer/paid-pages": "seo.competitor_ads",
    "site-explorer/all-backlinks": "seo.backlinks",
    "site-explorer/refdomains": "seo.backlinks",
    "site-explorer/pages-by-traffic": "seo.competitor_traffic",
    "site-explorer/organic-keywords": "seo.competitor_traffic",
}


def _endpoint_key(endpoint: str) -> str:
    value = endpoint.strip()
    value = value.replace("https://api.ahrefs.com/v3/", "")
    value = value.replace("/v3/", "")
    return value.strip("/")


def _records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("keywords", "competitors", "pages", "backlinks", "refdomains", "rows", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]
    return []


def _safe_num(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _money_from_cents(value: Any) -> float | None:
    number = _safe_num(value)
    return round(number / 100.0, 2) if number is not None else None


def _keyword_evidence(rows: list[dict[str, Any]], context: dict[str, Any]) -> list[dict[str, Any]]:
    if not rows:
        return []
    volumes = [
        int(v) for row in rows
        if (v := _safe_num(row.get("volume") if row.get("volume") is not None else row.get("volume_monthly"))) is not None
    ]
    cpcs = [
        v for row in rows
        if (v := _money_from_cents(row.get("cpc"))) is not None
    ]
    top = sorted(
        rows,
        key=lambda row: _safe_num(row.get("volume") if row.get("volume") is not None else row.get("volume_monthly")) or 0,
        reverse=True,
    )[:5]
    terms = [
        {
            "keyword": row.get("keyword"),
            "volume": row.get("volume") if row.get("volume") is not None else row.get("volume_monthly"),
            "cpc_usd": _money_from_cents(row.get("cpc")),
            "difficulty": row.get("difficulty"),
        }
        for row in top
    ]
    country = context.get("country")
    query = context.get("keywords") or context.get("query")
    claim = f"Ahrefs returned {len(rows)} keyword rows"
    if query:
        claim += f" for {query}"
    if country:
        claim += f" in {country}"
    if volumes:
        claim += f"; returned-row search volume sums to {sum(volumes):,}"
    if cpcs:
        claim += f"; median CPC across returned rows is USD {median(cpcs):.2f}"
    return [{
        "kind": "fact",
        "claim": claim + ".",
        "source_ref": context.get("source_ref") or "provider://ahrefs/keywords",
        "source_title": "Ahrefs Keywords Explorer",
        "confidence": 0.98,
        "notes": f"Top returned terms: {terms}. Aggregates apply only to the returned row set/limit, not the entire market.",
    }]


def _domain_rating_evidence(payload: dict[str, Any], context: dict[str, Any]) -> list[dict[str, Any]]:
    obj = payload.get("domain_rating")
    if not isinstance(obj, dict):
        return []
    dr = obj.get("domain_rating")
    rank = obj.get("ahrefs_rank")
    target = context.get("target") or "target"
    if dr is None and rank is None:
        return []
    parts = [f"Ahrefs reports {target}"]
    if dr is not None:
        parts.append(f"DR {dr}")
    if rank is not None:
        parts.append(f"Ahrefs Rank {rank}")
    return [{
        "kind": "fact",
        "claim": ", ".join(parts) + ".",
        "source_ref": context.get("source_ref") or f"provider://ahrefs/domain-rating/{target}",
        "source_title": "Ahrefs Site Explorer — Domain Rating",
        "confidence": 0.99,
    }]


def _competitor_evidence(rows: list[dict[str, Any]], context: dict[str, Any]) -> list[dict[str, Any]]:
    if not rows:
        return []
    top = sorted(rows, key=lambda r: _safe_num(r.get("traffic")) or 0, reverse=True)[:10]
    compact = [
        {
            "domain": r.get("competitor_domain") or r.get("competitor_url"),
            "dr": r.get("domain_rating"),
            "traffic": r.get("traffic"),
            "keywords_common": r.get("keywords_common"),
            "keywords_competitor": r.get("keywords_competitor"),
            "share": r.get("share"),
        }
        for r in top
    ]
    target = context.get("target") or "target"
    country = context.get("country")
    claim = f"Ahrefs returned {len(rows)} organic competitor rows for {target}"
    if country:
        claim += f" in {country}"
    return [{
        "kind": "fact",
        "claim": claim + ".",
        "source_ref": context.get("source_ref") or f"provider://ahrefs/organic-competitors/{target}",
        "source_title": "Ahrefs Site Explorer — Organic competitors",
        "confidence": 0.98,
        "notes": f"Top returned competitors by reported organic traffic: {compact}.",
    }]


def _paid_pages_evidence(rows: list[dict[str, Any]], context: dict[str, Any]) -> list[dict[str, Any]]:
    if not rows:
        return []
    active = [r for r in rows if (_safe_num(r.get("ads_count")) or 0) > 0 or (_safe_num(r.get("keywords")) or 0) > 0]
    target = context.get("target") or "target"
    top = sorted(active, key=lambda r: _safe_num(r.get("ads_count")) or 0, reverse=True)[:10]
    compact = [
        {
            "url": r.get("url") or r.get("page") or r.get("url_target"),
            "ads_count": r.get("ads_count"),
            "keywords": r.get("keywords"),
            "traffic": r.get("traffic"),
            "value": r.get("value"),
        }
        for r in top
    ]
    return [{
        "kind": "fact",
        "claim": f"Ahrefs returned {len(rows)} paid-page rows for {target}; {len(active)} returned rows show paid-search activity.",
        "source_ref": context.get("source_ref") or f"provider://ahrefs/paid-pages/{target}",
        "source_title": "Ahrefs Site Explorer — Paid pages",
        "confidence": 0.98,
        "notes": f"Top returned paid pages: {compact}.",
    }]


def _backlink_evidence(rows: list[dict[str, Any]], context: dict[str, Any]) -> list[dict[str, Any]]:
    if not rows:
        return []
    target = context.get("target") or "target"
    referring = set()
    for row in rows:
        domain = row.get("domain_ref") or row.get("refdomain") or row.get("domain_from")
        if domain:
            referring.add(str(domain))
    claim = f"Ahrefs returned {len(rows)} backlink/referring-domain rows for {target}"
    if referring:
        claim += f", spanning at least {len(referring)} distinct referring domains in the returned set"
    return [{
        "kind": "fact",
        "claim": claim + ".",
        "source_ref": context.get("source_ref") or f"provider://ahrefs/backlinks/{target}",
        "source_title": "Ahrefs Site Explorer — Backlinks",
        "confidence": 0.98,
        "notes": "Counts apply to the returned row set and request filters/limit.",
    }]


def normalize_ahrefs_result(
    *,
    request_id: str,
    endpoint: str,
    payload: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convert an official Ahrefs API/MCP payload into SAASskill's ToolResult envelope."""
    context = dict(context or {})
    key = _endpoint_key(endpoint)
    capability = ENDPOINT_CAPABILITY.get(key)
    if not capability:
        raise ValueError(f"Unsupported Ahrefs endpoint for automatic normalization: {key}")

    rows = _records(payload)
    if key.startswith("keywords-explorer/"):
        evidence = _keyword_evidence(rows, context)
    elif key == "site-explorer/domain-rating":
        evidence = _domain_rating_evidence(payload, context)
    elif key == "site-explorer/organic-competitors":
        evidence = _competitor_evidence(rows, context)
    elif key == "site-explorer/paid-pages":
        evidence = _paid_pages_evidence(rows, context)
    elif key in {"site-explorer/all-backlinks", "site-explorer/refdomains"}:
        evidence = _backlink_evidence(rows, context)
    else:
        target = context.get("target") or "target"
        evidence = [{
            "kind": "fact",
            "claim": f"Ahrefs returned {len(rows)} rows from {key} for {target}.",
            "source_ref": context.get("source_ref") or f"provider://ahrefs/{key}/{target}",
            "source_title": f"Ahrefs — {key}",
            "confidence": 0.98,
            "notes": "Automatic normalizer preserves the raw payload in data; synthesize only claims supported by returned fields.",
        }] if rows else []

    return {
        "request_id": request_id,
        "provider": "ahrefs",
        "capability": capability,
        "degraded": False,
        "status": "ok",
        "data": {"endpoint": key, "context": context, "raw": payload},
        "evidence": evidence,
        "state_patch": {},
    }
