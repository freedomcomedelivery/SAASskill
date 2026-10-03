from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from .capabilities import ADS_CAMPAIGNS_WRITE
from .state import utc_now

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


def _slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value[:48] or "finding"


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
    course_error_class: str | None = None,
) -> dict[str, Any]:
    fingerprint = f"{code}:{_slug(title)}"
    return {
        "id": f"finding_{_slug(fingerprint)}",
        "fingerprint": fingerprint,
        "code": code,
        "course_error_class": course_error_class,
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
            course_error_class="all_for_everyone",
        ))

    channels = snap.get("channels") or []
    completed_channels = [c for c in channels if isinstance(c, dict) and c.get("completed_iteration")]
    if len(channels) > 1 and not completed_channels:
        findings.append(_finding(
            "channel_scatter", "acquisition", "high",
            "Several channels are being tried before one is debugged",
            "Multiple acquisition channels exist in the snapshot but none has a completed comparable iteration.",
            "Choose one primary channel and debug it to a measurable conclusion before switching.",
            course_error_class="wrong_channel",
        ))

    searched = snap.get("product_is_searched")
    audience = snap.get("addressable_audience")
    primary_channel = snap.get("primary_channel")
    if searched is True and primary_channel and primary_channel not in {"search", "marketplace", "app_store_asa"}:
        findings.append(_finding(
            "wrong_channel_search_demand", "acquisition", "high",
            "Demand exists in search but primary GTM is elsewhere",
            f"Snapshot says the product is actively searched, while primary channel is {primary_channel}.",
            "Test or repair a search/software-marketplace funnel before diversifying.",
            course_error_class="wrong_channel",
        ))
    if searched is False and isinstance(audience, (int, float)) and audience < 10000 and primary_channel and primary_channel != "outreach":
        findings.append(_finding(
            "wrong_channel_small_market", "acquisition", "high",
            "Small non-searchable market is not using direct outreach",
            "The target audience is small and the product is not actively searched.",
            "Use targeted outreach as the controlled acquisition channel for the next test.",
            course_error_class="wrong_channel",
        ))

    if snap.get("controlled_funnel") is False or not snap.get("funnel_definition"):
        findings.append(_finding(
            "funnel_of_fate", "funnel", "blocking",
            "No controlled sales funnel",
            "The project cannot currently attribute outcomes through a defined reach/click/lead/qualified/payment path.",
            "Build one controlled funnel and send the target avatar through it before making product-level conclusions.",
            course_error_class="funnel_of_fate",
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
            course_error_class="no_decomposition_debugging",
        ))

    latest = (state.get("iterations") or [])[-1:]
    if latest:
        it = latest[0]
        actual = it.get("actual") or {}
        exposure = actual.get("reach") or actual.get("impressions") or 0
        leads = actual.get("leads") or 0
        days = actual.get("days") or actual.get("duration_days")
        conclusion = it.get("conclusion")
        if conclusion in {"channel_change_candidate", "idea_change_candidate"} and exposure < 1000 and leads < 20:
            findings.append(_finding(
                "premature_evaluation", "experimentation", "high",
                "Strong conclusion from a very small sample",
                "The latest iteration proposes a channel/idea-level conclusion before meaningful exposure/lead volume.",
                "Keep the funnel homogeneous, collect more complete data, and repeat before making a project-level conclusion.",
                course_error_class="premature_evaluation",
            ))
        if conclusion and isinstance(days, (int, float)) and days <= 2:
            findings.append(_finding(
                "rushing", "experimentation", "high",
                "Channel was judged after a very short run",
                f"The latest iteration records a conclusion after only {days:g} day(s).",
                "Let the selected channel/funnel run long enough to collect useful comparable data before changing the system.",
                course_error_class="rushing",
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

    return findings


def commercial_readiness(state: dict[str, Any], findings: list[dict[str, Any]] | None = None) -> str:
    findings = findings if findings is not None else derive_audit_findings(state)
    open_blockers = [f for f in findings if f.get("severity") == "blocking" and f.get("status", "open") == "open"]
    foundational_high = {
        "channel_scatter",
        "wrong_channel_search_demand",
        "wrong_channel_small_market",
        "sales_process_gap",
        "economics_unknown",
    }
    hard_high = [
        f for f in findings
        if f.get("status", "open") == "open" and f.get("code") in foundational_high
    ]
    snap = state.get("audit_snapshot") or {}
    funnel = snap.get("funnel") or {}
    payments = funnel.get("payments")
    if payments is None:
        payments = sum((x.get("payments") or 0) for x in state.get("funnel_snapshots", []))
    economics = state.get("economics") or snap.get("economics") or {}
    finished = [x for x in state.get("iterations", []) if x.get("actual") and x.get("conclusion")]

    if open_blockers or hard_high:
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
    existing_by_fp = {f.get("fingerprint"): f for f in existing if f.get("fingerprint")}
    current = derive_audit_findings(state)
    current_fps = {f["fingerprint"] for f in current}

    reconciled: list[dict[str, Any]] = []
    for finding in current:
        old = existing_by_fp.get(finding["fingerprint"])
        if old:
            finding["id"] = old.get("id", finding["id"])
            finding["first_seen_at"] = old.get("first_seen_at") or old.get("created_at") or utc_now()
        else:
            finding["first_seen_at"] = utc_now()
        finding["last_seen_at"] = utc_now()
        finding["status"] = "open"
        reconciled.append(finding)

    for old in existing:
        fp = old.get("fingerprint")
        if fp and fp not in current_fps:
            archived = deepcopy(old)
            archived["status"] = "resolved"
            archived.setdefault("resolved_at", utc_now())
            reconciled.append(archived)

    report["findings"] = reconciled
    report.setdefault("sections", {})
    report["commercial_readiness"] = commercial_readiness(state, current)
    report["updated_at"] = utc_now()
    state["commercial_readiness"] = report["commercial_readiness"]
    state["audit_report"] = report
    return report


def mark_audit_section(
    state: dict[str, Any],
    section: str,
    *,
    summary: str,
    evidence_ids: list[str],
    status: str = "audited",
) -> dict[str, Any]:
    if status not in {"audited", "complete", "pass"}:
        raise ValueError("audit section status must be audited, complete or pass")
    report = refresh_audit_report(state)
    report.setdefault("sections", {})[section] = {
        "status": status,
        "summary": summary,
        "evidence_ids": list(evidence_ids),
        "updated_at": utc_now(),
    }
    state["audit_report"] = report
    return report["sections"][section]


def growth_priorities(state: dict[str, Any]) -> list[dict[str, Any]]:
    report = refresh_audit_report(state)
    order = {"blocking": 0, "high": 1, "medium": 2, "low": 3}
    open_findings = [f for f in report.get("findings", []) if f.get("status") == "open"]
    open_findings.sort(key=lambda x: (order.get(x.get("severity"), 9), x.get("area", "")))
    return [
        {
            "finding_id": f["id"],
            "finding_fingerprint": f["fingerprint"],
            "code": f["code"],
            "priority": i + 1,
            "area": f["area"],
            "severity": f["severity"],
            "problem": f["title"],
            "action": f["recommendation"],
        }
        for i, f in enumerate(open_findings)
    ]


def build_growth_plan(state: dict[str, Any]) -> dict[str, Any]:
    report = refresh_audit_report(state)
    priorities = growth_priorities(state)
    actionable_priorities = [
        p for p in priorities
        if not (report["commercial_readiness"] == "ready_for_controlled_sales" and p.get("code") == "no_payment_signal")
    ]
    actions: list[dict[str, Any]] = []

    for p in actionable_priorities:
        actions.append({
            "id": f"action_{_slug(p['finding_fingerprint'])}",
            "finding_id": p["finding_id"],
            "description": p["action"],
            "hypothesis": f"Resolving {p['problem']} will improve commercial readiness or the earliest broken funnel step.",
            "capability": None,
            "side_effect": False,
            "status": "planned",
        })

    readiness = report["commercial_readiness"]
    snap = state.get("audit_snapshot") or {}
    primary_channel = snap.get("primary_channel")
    ad_channels = {"search", "meta", "google_display", "rsya", "app_store_asa"}

    if not actions and readiness == "ready_for_controlled_sales":
        actions.append({
            "id": "action_controlled_sales_test",
            "finding_id": None,
            "description": "Run one controlled sales test through the selected primary channel and measure through qualified leads and payments.",
            "hypothesis": "A coherent offer and funnel will produce a measurable qualified-lead/payment signal from the target avatar.",
            "capability": ADS_CAMPAIGNS_WRITE if primary_channel in ad_channels else None,
            "side_effect": True,
            "status": "planned",
        })
    elif not actions and readiness == "sales_validated":
        actions.append({
            "id": "action_improve_repeatability",
            "finding_id": None,
            "description": "Repeat the validated funnel with a controlled budget and improve CAC/repeatability before scaling.",
            "hypothesis": "The payment signal can be reproduced without degrading target-lead quality or economics.",
            "capability": ADS_CAMPAIGNS_WRITE if primary_channel in ad_channels else None,
            "side_effect": True,
            "status": "planned",
        })
    elif not actions and readiness == "ready_to_scale":
        actions.append({
            "id": "action_scale_primary_channel",
            "finding_id": None,
            "description": "Scale the proven primary channel gradually while monitoring qualified-lead share, CAC and payment conversion.",
            "hypothesis": "Increasing exposure can preserve funnel quality and viable economics.",
            "capability": ADS_CAMPAIGNS_WRITE if primary_channel in ad_channels else None,
            "side_effect": True,
            "status": "planned",
        })

    plan = {
        "readiness": readiness,
        "priorities": priorities,
        "actions": actions,
        "generated_at": utc_now(),
    }
    state["growth_plan"] = plan
    if actions:
        state["selected_growth_action_id"] = actions[0]["id"]
    return plan


def update_growth_action(state: dict[str, Any], action_id: str, status: str) -> dict[str, Any]:
    allowed = {"planned", "prepared", "approved", "running", "executed", "measured", "cancelled"}
    if status not in allowed:
        raise ValueError(f"Invalid growth action status: {status}")
    actions = (state.get("growth_plan") or {}).get("actions") or []
    action = next((x for x in actions if x.get("id") == action_id), None)
    if action is None:
        raise ValueError(f"Growth action not found: {action_id}")
    action["status"] = status
    action["updated_at"] = utc_now()
    return action
