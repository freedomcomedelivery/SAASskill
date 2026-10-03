from __future__ import annotations

import csv
import io
from statistics import median
from typing import Any

REPORT_CAPABILITY = {
    "phrase_all": "seo.keyword_metrics",
    "phrase_these": "seo.keyword_metrics",
    "phrase_fullsearch": "seo.keyword_metrics",
    "phrase_related": "seo.keyword_metrics",
    "phrase_questions": "seo.keyword_metrics",
    "phrase_kdi": "seo.keyword_metrics",
    "domain_ranks": "seo.domain_metrics",
    "domain_rank": "seo.domain_metrics",
    "domain_organic": "seo.competitor_traffic",
    "domain_organic_organic": "seo.competitor_traffic",
    "domain_adwords": "seo.competitor_ads",
    "phrase_adwords": "seo.competitor_ads",
    "phrase_adwords_historical": "seo.competitor_ads",
    "backlinks": "seo.backlinks",
    "backlinks_overview": "seo.backlinks",
    "referring_domains": "seo.backlinks",
}

ALIASES = {
    "keyword": ["Keyword", "keyword", "Ph"],
    "volume": ["Search Volume", "Volume", "search_volume", "volume", "Nq"],
    "cpc": ["CPC", "cpc", "Cp"],
    "competition": ["Competition", "competition", "Co"],
    "difficulty": ["Keyword Difficulty", "Keyword Difficulty Index", "difficulty", "Kd"],
    "domain": ["Domain", "domain", "Dn"],
    "organic_traffic": ["Organic Traffic", "organic_traffic", "Ot"],
    "organic_keywords": ["Organic Keywords", "organic_keywords", "Or"],
    "paid_traffic": ["Adwords Traffic", "Paid Traffic", "paid_traffic", "At"],
    "paid_keywords": ["Adwords Keywords", "Paid Keywords", "paid_keywords", "Ad"],
    "common_keywords": ["Common Keywords", "common_keywords", "Np"],
    "backlinks": ["Backlinks", "backlinks", "backlinks_count"],
    "refdomains": ["Referring Domains", "referring_domains", "domains_count"],
}


def _rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, str):
        text = payload.strip()
        if not text:
            return []
        reader = csv.DictReader(io.StringIO(text), delimiter=";")
        return [dict(row) for row in reader if row]
    if isinstance(payload, list):
        return [dict(x) for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in ("data", "rows", "results", "keywords", "domains", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [dict(x) for x in value if isinstance(x, dict)]
        return [payload]
    raise TypeError("Semrush payload must be CSV text, list or dict")


def _get(row: dict[str, Any], logical: str) -> Any:
    for key in ALIASES[logical]:
        if key in row and row[key] not in ("", None):
            return row[key]
    return None


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def normalize_semrush_result(
    *,
    request_id: str,
    report_type: str,
    payload: Any,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    context = dict(context or {})
    capability = REPORT_CAPABILITY.get(report_type)
    if not capability:
        raise ValueError(f"Unsupported Semrush report type: {report_type}")
    rows = _rows(payload)
    evidence: list[dict[str, Any]] = []
    source_ref = context.get("source_ref") or f"provider://semrush/{report_type}"
    target = context.get("target") or context.get("query") or context.get("phrase") or "target"

    if capability == "seo.keyword_metrics":
        volumes = [x for r in rows if (x := _num(_get(r, "volume"))) is not None]
        cpcs = [x for r in rows if (x := _num(_get(r, "cpc"))) is not None]
        top = sorted(rows, key=lambda r: _num(_get(r, "volume")) or 0, reverse=True)[:10]
        summary = []
        for r in top:
            summary.append({
                "keyword": _get(r, "keyword"),
                "volume": _num(_get(r, "volume")),
                "cpc": _num(_get(r, "cpc")),
                "competition": _num(_get(r, "competition")),
                "difficulty": _num(_get(r, "difficulty")),
            })
        claim = f"Semrush returned {len(rows)} keyword rows for {target}"
        if volumes:
            claim += f"; returned-row search volume sums to {int(sum(volumes)):,}"
        if cpcs:
            claim += f"; median CPC is {median(cpcs):.2f}"
        evidence.append({
            "kind": "fact",
            "claim": claim + ".",
            "source_ref": source_ref,
            "source_title": f"Semrush {report_type}",
            "confidence": 0.98,
            "notes": f"Top returned rows: {summary}. Aggregates apply only to returned rows and filters.",
        })

    elif capability == "seo.domain_metrics":
        first = rows[0] if rows else {}
        metrics = {
            "organic_keywords": _num(_get(first, "organic_keywords")),
            "organic_traffic": _num(_get(first, "organic_traffic")),
            "paid_keywords": _num(_get(first, "paid_keywords")),
            "paid_traffic": _num(_get(first, "paid_traffic")),
        }
        evidence.append({
            "kind": "fact",
            "claim": f"Semrush domain metrics for {target}: {metrics}.",
            "source_ref": source_ref,
            "source_title": f"Semrush {report_type}",
            "confidence": 0.98,
        })

    elif capability == "seo.competitor_traffic":
        top = sorted(rows, key=lambda r: _num(_get(r, "organic_traffic")) or 0, reverse=True)[:10]
        compact = [{
            "domain": _get(r, "domain"),
            "common_keywords": _num(_get(r, "common_keywords")),
            "organic_traffic": _num(_get(r, "organic_traffic")),
            "organic_keywords": _num(_get(r, "organic_keywords")),
            "paid_keywords": _num(_get(r, "paid_keywords")),
        } for r in top]
        evidence.append({
            "kind": "fact",
            "claim": f"Semrush returned {len(rows)} domain/competitor rows for {target}.",
            "source_ref": source_ref,
            "source_title": f"Semrush {report_type}",
            "confidence": 0.98,
            "notes": f"Top returned rows by organic traffic: {compact}.",
        })

    elif capability == "seo.competitor_ads":
        evidence.append({
            "kind": "fact",
            "claim": f"Semrush returned {len(rows)} paid-search/ad rows for {target}.",
            "source_ref": source_ref,
            "source_title": f"Semrush {report_type}",
            "confidence": 0.98,
            "notes": "Use the raw rows for ad copy, paid keywords and competitor-specific details.",
        })

    else:
        first = rows[0] if rows else {}
        counts = {
            "backlinks": _num(_get(first, "backlinks")),
            "referring_domains": _num(_get(first, "refdomains")),
        }
        evidence.append({
            "kind": "fact",
            "claim": f"Semrush backlink data for {target}: {counts}; returned rows={len(rows)}.",
            "source_ref": source_ref,
            "source_title": f"Semrush {report_type}",
            "confidence": 0.98,
        })

    return {
        "request_id": request_id,
        "provider": "semrush",
        "capability": capability,
        "degraded": False,
        "status": "ok",
        "data": {"report_type": report_type, "context": context, "rows": rows, "raw": payload},
        "evidence": evidence,
        "state_patch": {},
    }
