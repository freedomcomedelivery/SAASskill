from __future__ import annotations

from typing import Any


def _rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [dict(x) for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in ("results", "data", "rows", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [dict(x) for x in value if isinstance(x, dict)]
        return [payload]
    return []


def normalize_crm_result(*, provider: str, request_id: str, payload: Any, context: dict[str, Any] | None = None) -> dict[str, Any]:
    if provider not in {"hubspot", "crm"}:
        raise ValueError(f"Unsupported CRM provider: {provider}")
    context = dict(context or {})
    rows = _rows(payload)
    qualified_stages = {str(x).lower() for x in context.get("qualified_stages", ["qualified", "mql", "sql", "salesqualifiedlead", "opportunity"])}
    paid_stages = {str(x).lower() for x in context.get("paid_stages", ["closedwon", "paid", "customer"])}

    qualified = 0
    paid = 0
    for row in rows:
        props = row.get("properties") if isinstance(row.get("properties"), dict) else row
        stage = str(
            props.get(context.get("stage_field", "lifecyclestage"))
            or props.get("dealstage")
            or props.get("stage")
            or props.get("status")
            or ""
        ).lower()
        is_paid = stage in paid_stages or props.get("paid") is True
        is_qualified = stage in qualified_stages or props.get("qualified") is True or is_paid
        qualified += int(is_qualified)
        paid += int(is_paid)

    leads = len(rows)
    merge_patch = {}
    if context.get("workflow") == "existing_project_audit":
        merge_patch = {
            "audit_snapshot": {
                "crm": {"provider": provider, "connected": True},
                "funnel": {"leads": leads, "qualified_leads": qualified},
                "sales_process": {"crm_observed": True, "observed_paid_stage_count": paid},
            }
        }

    return {
        "request_id": request_id,
        "provider": provider,
        "capability": "crm.leads.read",
        "degraded": False,
        "status": "ok",
        "data": {"rows": rows, "summary": {"leads": leads, "qualified_leads": qualified, "paid_stage_count": paid}},
        "evidence": [{
            "kind": "fact",
            "claim": f"{provider} returned {leads} CRM records; {qualified} match qualified stages and {paid} match paid/customer stages.",
            "source_ref": context.get("source_ref") or f"provider://{provider}/leads",
            "source_title": f"{provider} CRM leads/deals",
            "confidence": 0.97,
            "notes": "CRM paid/customer stages are not treated as verified processor payment evidence.",
        }],
        "state_patch": {},
        "state_merge_patch": merge_patch,
    }
