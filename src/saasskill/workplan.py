from __future__ import annotations

from typing import Any

from .gates import evaluate_stage


def _item(kind: str, key: str, description: str, *, autonomous: bool = True, provider_hint: str | None = None) -> dict[str, Any]:
    return {"kind": kind, "key": key, "description": description, "autonomous": autonomous, "provider_hint": provider_hint}


def build_work_queue(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Translate current stage/gate gaps into executable host work items."""
    stage = state.get("stage", "intake")
    gate = evaluate_stage(state, stage)
    q: list[dict[str, Any]] = []

    if gate.status == "needs_simplification":
        return [_item("decision", "simplify", gate.next_action or "Simplify project scope.", autonomous=False)]

    if stage == "intake":
        if gate.passed:
            q.append(_item("state", "personal_constraints", "Capture only personal constraints that materially change project choice.", autonomous=False))
        return q

    if stage == "personal_concept":
        if not gate.passed:
            q.append(_item("user_input", "personal_concept", gate.next_action or "Capture personal constraints.", autonomous=False))
        else:
            q.append(_item("research", "candidate_markets", "Find candidate markets consistent with project constraints.", provider_hint="web"))
        return q

    if stage == "market_discovery":
        q.extend([
            _item("research", "market_players", "Find multiple current players and close reference products.", provider_hint="web"),
            _item("research", "market_demand", "Find transaction/demand traces; separate search demand from willingness to pay.", provider_hint="web/seo"),
            _item("research", "market_structure", "Check switching cost, concentration, traffic dominance and geo relevance.", provider_hint="web/seo"),
        ])
        return q

    if stage == "idea_generation":
        q.extend([
            _item("research", "reference_products", "Find real reference products before treating generated ideas as viable.", provider_hint="web"),
            _item("artifact", "idea_shortlist", "Generate ideas inside evidenced markets and store them as idea cards."),
        ])
        return q

    if stage == "idea_selection":
        idea = next((i for i in state.get("ideas", []) if i.get("id") == state.get("selected_idea_id") or i.get("decision") == "selected"), {})
        if len(idea.get("references") or []) < 3:
            q.append(_item("research", "close_references", "Find 3–5 close references, preferably same geo/avatar/pain/solution.", provider_hint="web"))
        if idea.get("avg_competitor_check") is None:
            q.append(_item("research", "competitor_pricing", "Collect current competitor pricing.", provider_hint="web"))
        if not idea.get("usage_frequency"):
            q.append(_item("research", "usage_frequency", "Estimate usage frequency from product/review evidence.", provider_hint="web"))
        if idea.get("feasible_as_pet_project") is None or idea.get("personal_fit") is None:
            q.append(_item("user_input", "feasibility_fit", "Resolve only feasibility/personal-fit facts that cannot be researched.", autonomous=False))
        return q

    if stage == "research_marketing":
        q.extend([
            _item("research", "competitor_products", "Use/review direct competitors and capture mechanism, price and market norms.", provider_hint="web"),
            _item("research", "reviews_users", "Analyze reviews, demos/videos and paying-user context.", provider_hint="web"),
            _item("research", "traffic_channels", "Inspect competitor acquisition channels and current ads where possible.", provider_hint="seo/ads"),
            _item("artifact", "marketing_contract", "Build one coherent avatar → situation → pain → solution → primary benefit contract."),
        ])
        return q

    if stage == "offer_landing":
        q.extend([
            _item("artifact", "landing_brief", "Create one-avatar, one-channel, one-CTA landing brief from marketing contract."),
            _item("technical", "measurement_plan", "Define lead/payment analytics events, notifications and technical checks."),
        ])
        return q

    if stage == "gtm_planning":
        channel = (state.get("channel_plan") or {}).get("channel")
        q.append(_item("research", "platform_current_check", f"Verify current rules/UI for {channel or 'candidate channel'} before execution.", provider_hint="web"))
        q.append(_item("calculation", "experiment_economics", "Calculate budget cap, expected funnel, CAC/LTV assumptions and stopping conditions."))
        if channel == "search":
            q.append(_item("research", "search_keywords", "Collect hot transactional keywords, volume, CPC/competition and competitor ads.", provider_hint="seo/ads"))
        elif channel == "meta":
            q.append(_item("research", "meta_creatives", "Research competitor creatives and prepare 1–2 tightly matched hypotheses.", provider_hint="ads"))
        elif channel == "telegram":
            q.append(_item("research", "telegram_channels", "Find/filter author-led channels by reach, ad return proxies, audience source and price.", provider_hint="web"))
        elif channel == "outreach":
            q.append(_item("research", "prospect_base", "Build a qualified prospect base and source provenance.", provider_hint="prospecting"))
        return q

    if stage == "launch":
        approved = [a for a in state.get("approvals", []) if a.get("status") == "approved"]
        if not approved:
            q.append(_item("approval", "launch_approval", "Request approval with exact target, max spend, duration, assets and pause condition.", autonomous=False))
        else:
            q.append(_item("action", "execute_launch", "Execute only the approved external action and read back the result.", provider_hint="ads/action"))
        return q

    if stage == "lead_onboarding":
        q.extend([
            _item("metrics", "lead_intake", "Read incoming leads and qualification outcomes.", provider_hint="crm/analytics"),
            _item("operation", "manual_onboarding", "Prioritize qualified leads and capture objections, activation and payment asks."),
        ])
        return q

    if stage == "iteration_tracking":
        q.extend([
            _item("metrics", "funnel_snapshot", "Read observed reach → clicks → leads → qualified leads → payments.", provider_hint="analytics/ads"),
            _item("analysis", "diagnose_earliest_break", "Diagnose the earliest meaningful funnel break and change the smallest useful variable set."),
        ])
        return q

    if stage == "scale_or_pivot":
        q.append(_item("decision", "decision_memo", "Separate channel failure, offer failure and idea failure using repeated finished iterations.", autonomous=False))
        return q

    return q
