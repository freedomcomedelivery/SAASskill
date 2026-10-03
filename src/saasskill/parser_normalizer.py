from __future__ import annotations

from typing import Any


def normalize_public_page_result(
    *,
    request_id: str,
    snapshot: dict[str, Any],
    context: dict[str, Any] | None = None,
    provider: str = "camoufox",
    capability: str = "web.browser_parse",
) -> dict[str, Any]:
    context = dict(context or {})
    url = snapshot.get("url") or snapshot.get("requested_url") or context.get("url") or "page"
    title = snapshot.get("title") or ""
    ctas = snapshot.get("ctas") or []
    prices = snapshot.get("prices") or []
    forms = snapshot.get("forms")
    challenge = bool(snapshot.get("challenge_detected") or snapshot.get("blocked_by_challenge"))

    evidence = [{
        "kind": "fact",
        "claim": (
            f"Public page {url} was parsed"
            + (f" with title '{title}'" if title else "")
            + f"; CTAs={len(ctas)}, visible price tokens={len(prices)}, forms={forms if forms is not None else 'unknown'}."
        ),
        "source_ref": url if str(url).startswith(("http://", "https://")) else f"provider://{provider}/page",
        "source_title": title or "Public product page",
        "confidence": 0.97,
        "notes": f"CTAs: {ctas[:20]}; prices: {prices[:20]}; challenge_detected={challenge}.",
    }]

    merge_patch: dict[str, Any] = {}
    if context.get("workflow") == "existing_project_audit":
        merge_patch = {
            "audit_snapshot": {
                "product_url": snapshot.get("requested_url") or snapshot.get("url"),
                "landing": {
                    "title": title,
                    "meta_description": snapshot.get("meta_description"),
                    "headings": snapshot.get("headings") or [],
                    "ctas": ctas,
                    "cta_count": len(ctas),
                    "forms": forms,
                    "inputs": snapshot.get("inputs") or [],
                    "prices": prices,
                    "challenge_detected": challenge,
                },
            }
        }

    return {
        "request_id": request_id,
        "provider": provider,
        "capability": capability,
        "degraded": capability != "web.browser_parse",
        "status": "ok",
        "data": {"snapshot": snapshot, "context": context},
        "evidence": evidence,
        "state_patch": {},
        "state_merge_patch": merge_patch,
    }
