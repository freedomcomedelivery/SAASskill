from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Any

COURSE_ERROR_CLASSES = {
    "wrong_channel": "Wrong traffic channel / channel scatter",
    "rushing": "Rushing: evaluating a channel before it has worked long enough",
    "all_for_everyone": "All-for-everyone: weak segmentation and too many primary avatars",
    "funnel_of_fate": "Funnel of fate: uncontrolled launch instead of a measurable sales funnel",
    "premature_evaluation": "Premature evaluation from incomplete/noisy data",
    "no_decomposition_debugging": "No funnel decomposition and systematic debugging",
}


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def _count_primary(value: Any) -> int:
    if isinstance(value, list):
        return len([x for x in value if _present(x)])
    return 1 if _present(value) else 0


def _finding(
    code: str,
    area: str,
    severity: str,
    title: str,
    observation: str,
    recommendation: str,
    *,
    evidence_ids: list[str] | None = None,
    source: str = "course_methodology",
) -> dict[str, Any]:
    return {
        "id": f"finding_{uuid.uuid4().hex[:8]}",
        "code": code,
        "area": area,
        "severity": severity,
        "title": title,
        "observation": observation,
        "recommendation": recommendation,
        "evidence_ids": evidence_ids or [],
        "source": source,
        "status": "open",
    }


def derive_audit_findings(state: dict[str, Any]) -> list[dict[str, Any]]:
    snap = state.get("audit_snapshot") or {}
    report = state.get("audit_report") or {}
    findings: list[dict[str, Any]] = []

    avatars = snap.get("avatars") or snap.get("avatar")
    pains = snap.get("pains") or snap.get("pain")
    benefits = snap.get("benefits") or snap.get("primary_benefit")
    if _count_primary(avatars) != 1 or _count_primary(pains) != 1 or _count_primary(benefits) != 1:
        findings.append(_finding(
            "all_for_everyone", "positioning", "blocking",
            "No single avatar → pain → benefit chain",
            "The existing project is not narrowed to one primary commercial segment/problem/benefit.",
            "Choose one primary avatar, one primary pain and one primary benefit for the next controlled sales funnel.",
        ))

    channels = snap.get("channels") or []
    completed_channels = [c for c in channels if isinstance(c, dict) and c.get("completed_iteration")]
    if len(channels) > 1 and not completed_channels:
        findings.append(_finding(
            "wrong_channel", "acquisition", "high",
            "Channel scatter before one channel is debugged",
            "Several channels are being tried without a finished, comparable iteration.",
            "Choose one channel according to demand/audience logic and debug it to a measurable conclusion before switching.",
        ))

    searched = snap.get("product_is_searched")
    audience = snap.get("addressable_audience")
    primary_channel = snap.get("primary_channel")
    if searched is True and primary_channel and primary_channel not in {"search", "marketplace", "app_store_asa"}:
        findings.append(_finding(
            "wrong_channel", "acquisition", "high",
            "Demand exists in search but primary GTM is elsewhere",
            f"Snapshot says the product is actively searched, while primary channel is {primary_channel}.",
            "Test/repair a search or software-marketplace funnel before diversifying.",
        ))
    if searched is False and isinstance(audience, (int, float)) and audience < 10000 and primary_channel and primary_channel != "outreach":
        findings.append(_finding(
            "wrong_channel", "acquisition", "high",
            "Small non-searchable market is not using direct outreach",
            "The target audience is small and the product is not actively searched.",
            "Use targeted outreach as the controlled acquisition channel for the next test.",
        ))

    if snap.get("controlled_funnel") is False or not snap.get("funnel_definition"):
        findings.append(_finding(
            "funnel_of_fate", "funnel", "blocking",
            "No controlled sales funnel",
            "The project cannot currently attribute outcomes through a defined reach/click/lead/qualified/payment path.",
            "Build one controlled funnel and send the target avatar through it before making product-level conclusions.",
        ))

    analytics = snap.get("analytics") or {}
    funnel = snap.get("funnel") or {}
    required = ["reach", "clicks", "leads", "qualified_leads", "payments"]
    missing_metrics = [k for k in required if funnel.get(k) is None]
    if not analytics.get("configured") or len(missing_metrics) >= 2:
        findings.append(_finding(
            "no_decomposition_debugging", "analytics", "blocking",
            "Funnel cannot be decomposed",
            f"Missing or unreliable metrics: {', '.join(missing_metrics) if missing_metrics else 'analytics configuration'}.",
            "Instrument the funnel and review the earliest meaningful break instead of judging the whole project at once.",
        ))

    latest = (state.get("iterations") or [])[-1:] 
    if latest:
        it = latest[0]
        actual = it.get("actual") or {}
        exposure = actual.get("reach") or actual.get("impressions") or 0
        leads = actual.get("leads") or 0
        conclusion = it.get("conclusion")
        if conclusion in {"channel_change_candidate", "idea_change_candidate"} and exposure < 1000 and leads < 20:
            findings.append(_finding(
                "premature_evaluation", "experimentation", "high",
                "Strong conclusion from a very small sample",
                "The latest iteration proposes a channel/idea-level conclusion before meaningful exposure/lead volume.",
                "Keep the funnel homogeneous, collect more complete data, and repeat before making a project-level conclusion.",
            ))

    sales = snap.get("sales_process") or {}
    sales_stages = {
        "qualification": sales.get("qualification"),
        "need": sales.get("need_discovery"),
        "value": sales.get("demo_or_value_delivery"),
        "close": sales.get("close_or_payment_ask"),
    }
    missing_sales = [k for k, v in sales_stages.items() if not _present(v)]
    if missing_sales:
        findings.append(_finding(
            "sales_process_gap", "sales", "high",
            "Early sales process is incomplete",
            f"Missing early-stage sales steps: {', '.join(missing_sales)}.",
            "For the first customers, explicitly qualify, understand the need, deliver/demo value and ask for payment; record where qualified leads drop.",
        ))

    offer = snap.get("offer") or {}
    landing = snap.get("landing") or {}
    if not _present(offer.get("primary_cta")) or not _present(offer.get("primary_benefit")):
        findings.append(_finding(
            "offer_gap", "offer", "blocking",
            "Offer is not explicit enough to sell",
            "The commercial offer lacks a single primary benefit and/or primary CTA.",
            "Build one offer for the chosen avatar and pain, with one CTA and a concrete reason to buy now.",
        ))
    if landing and landing.get("cta_count", 1) > 1:
        findings.append(_finding(
            "landing_multiple_cta", "landing", "high",
            "Landing has multiple primary actions",
            "The page asks the visitor to take several different actions.",
            "Reduce the launch landing to one primary CTA for one channel/avatar.",
        ))
    if landing and landing.get("mechanism_visible") is False:
        findings.append(_finding(
            "landing_mechanism_gap", "landing", "medium",
            "Product mechanism/value delivery is not visible",
            "The page promises an outcome without clearly showing how the product works.",
            "Show the mechanism/product workflow and visual proof near the primary benefit.",
        ))

    economics = state.get("economics") or snap.get("economics") or {}
    if economics.get("target_cac") is None or (economics.get("ltv_estimate") is None and economics.get("price") is None):
        findings.append(_finding(
            "economics_unknown", "economics", "high",
            "No commercial constraint for paid acquisition",
            "There is no usable target CAC versus LTV/price model.",
            "Calculate a conservative target CAC and budget cap before paid traffic.",
        ))

    payments = funnel.get("payments")
    if payments is None:
        payments = sum((x.get("payments") or 0) for x in state.get("funnel_snapshots", []))
    if payments == 0 and snap.get("product_status") in {"live", "launched"}:
        findings.append(_finding(
            "no_payment_signal", "sales", "high",
            "Live product has no recorded payment signal",
            "The product is launched but the audit snapshot contains no verified payments.",
            "Prioritize a controlled funnel and explicit payment ask before feature expansion.",
        ))

    existing_codes = {f.get("code") for f in report.get("findings", [])}
    return [f for f in findings if f["code"] not in existing_codes]


def commercial_readiness(state: dict[str, Any], findings: list[dict[str, Any]] | None = None) -> str:
    findings = findings if findings is not None else derive_audit_findings(state)
    open_blockers = [f for f in findings if f.get("severity") == "blocking" and f.get("status", "open") == "open"]
    snap = state.get("audit_snapshot") or {}
    funnel = snap.get("funnel") or {}
    payments = funnel.get("payments")
    if payments is None:
        payments = sum((x.get("payments") or 0) for x in state.get("funnel_snapshots", []))
    economics = state.get("economics") or snap.get("economics") or {}
    finished = [x for x in state.get("iterations", []) if x.get("actual") and x.get("conclusion")]

    if open_blockers:
        return "not_ready"
    if not payments:
        return "ready_for_controlled_sales"
    viable = economics.get("viability") == "pass"
    if payments and not (viable and finished):
        return "sales_validated"
    return "ready_to_scale"


def refresh_audit_report(state: dict[str, Any]) -> dict[str, Any]:
    report = deepcopy(state.get("audit_report") or {})
    existing = report.get("findings", [])
    new = derive_audit_findings({**state, "audit_report": report})
    report["findings"] = existing + new
    report.setdefault("sections", {})
    report["commercial_readiness"] = commercial_readiness(state, report["findings"])
    state["commercial_readiness"] = report["commercial_readiness"]
    state["audit_report"] = report
    return report


def growth_priorities(state: dict[str, Any]) -> list[dict[str, Any]]:
    report = refresh_audit_report(state)
    order = {"blocking": 0, "high": 1, "medium": 2, "low": 3}
    open_findings = [f for f in report.get("findings", []) if f.get("status", "open") == "open"]
    open_findings.sort(key=lambda x: (order.get(x.get("severity"), 9), x.get("area", "")))
    return [
        {
            "finding_id": f["id"],
            "priority": i + 1,
            "area": f["area"],
            "severity": f["severity"],
            "problem": f["title"],
            "action": f["recommendation"],
        }
        for i, f in enumerate(open_findings)
    ]
