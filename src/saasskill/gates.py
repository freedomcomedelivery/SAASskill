from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class GateResult:
    stage: str
    status: str
    reasons: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    next_action: str | None = None

    @property
    def passed(self) -> bool:
        return self.status == "pass"

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "status": self.status,
            "reasons": self.reasons,
            "missing": self.missing,
            "next_action": self.next_action,
        }


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def _selected_idea(state: dict[str, Any]) -> dict[str, Any] | None:
    selected_id = state.get("selected_idea_id")
    for idea in state.get("ideas", []):
        if idea.get("id") == selected_id or idea.get("decision") == "selected":
            return idea
    return None


def _single_value(value: Any) -> bool:
    if isinstance(value, list):
        return len([x for x in value if _present(x)]) == 1
    return _present(value)


def _simplification_problems(state: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    mc = state.get("marketing_contract") or {}
    for key, label in [
        ("avatar", "primary avatar"),
        ("pain", "primary pain"),
        ("primary_benefit", "primary benefit"),
    ]:
        value = mc.get(key)
        if isinstance(value, list) and len([x for x in value if _present(x)]) > 1:
            problems.append(f"Multiple {label}s are marked as primary.")
    cp = state.get("channel_plan") or {}
    channel = cp.get("channel")
    if isinstance(channel, list) and len(channel) > 1:
        problems.append("Multiple primary GTM channels selected.")
    if state.get("selected_idea_id") is None:
        selected = [x for x in state.get("ideas", []) if x.get("decision") == "selected"]
        if len(selected) > 1:
            problems.append("Multiple ideas are selected.")
    return problems


def _pass(stage: str, *reasons: str, next_action: str | None = None) -> GateResult:
    return GateResult(stage, "pass", list(reasons), [], next_action)


def _need(stage: str, status: str, missing: list[str], next_action: str) -> GateResult:
    return GateResult(stage, status, [], missing, next_action)


def evaluate_stage(state: dict[str, Any], stage: str | None = None) -> GateResult:
    stage = stage or state.get("stage", "intake")

    simplify = _simplification_problems(state)
    if simplify and stage not in {"intake", "personal_concept"}:
        return GateResult(
            stage,
            "needs_simplification",
            reasons=simplify,
            next_action="Narrow to one avatar, one pain, one benefit, one idea and one GTM.",
        )

    if stage == "intake":
        missing = []
        if not _present(state.get("project_id")):
            missing.append("project_id")
        if not _present(state.get("name")):
            missing.append("name")
        if missing:
            return _need(stage, "needs_user_input", missing, "Define project identity.")
        return _pass(stage, "Project identity exists.", next_action="Capture only constraints that materially affect project choice.")

    if stage == "personal_concept":
        pc = state.get("personal_concept") or {}
        if _selected_idea(state):
            return _pass(stage, "Concrete selected idea makes personal-concept stage non-blocking.", next_action="Validate target market.")
        meaningful = [k for k, v in pc.items() if _present(v)]
        if not meaningful:
            return _need(
                stage,
                "needs_user_input",
                ["personal_concept"],
                "Capture skills/experience, interests or hard-no constraints, budget and nearest goal.",
            )
        return _pass(stage, f"Personal concept has {len(meaningful)} populated constraints.", next_action="Research candidate markets.")

    if stage == "market_discovery":
        markets = state.get("markets", [])
        if not markets:
            return _need(stage, "needs_evidence", ["markets"], "Research at least one concrete market.")
        viable = []
        for market in markets:
            refs = market.get("evidence_ids") or []
            players = market.get("players") or []
            green = market.get("green_signals") or {}
            if market.get("gate_status") == "pass" or (len(players) >= 3 and len(refs) >= 1 and bool(green)):
                viable.append(market)
        if not viable:
            return _need(
                stage,
                "needs_evidence",
                ["multiple players", "green-market signals", "evidence_ids"],
                "Ground a market with several players, demand/transaction traces, switching-cost and concentration evidence.",
            )
        return _pass(stage, f"{len(viable)} market candidate(s) have enough evidence.", next_action="Generate ideas inside evidenced markets.")

    if stage == "idea_generation":
        ideas = state.get("ideas", [])
        if not ideas:
            return _need(stage, "needs_evidence", ["ideas"], "Generate a shortlist from evidenced markets.")
        grounded = [i for i in ideas if _present(i.get("one_liner")) and len(i.get("references") or []) >= 1]
        if not grounded:
            return _need(stage, "needs_evidence", ["candidate references"], "Find real reference products for candidate ideas.")
        return _pass(stage, f"{len(grounded)} idea(s) have at least one reference.", next_action="Complete idea-readiness fields and select one.")

    if stage == "idea_selection":
        idea = _selected_idea(state)
        if not idea:
            return _need(stage, "needs_user_input", ["selected_idea_id"], "Select one idea from the shortlist.")
        missing = []
        if not _present(idea.get("one_liner")):
            missing.append("one_liner")
        if not _present(idea.get("primary_pain")):
            missing.append("primary_pain")
        if len(idea.get("references") or []) < 3:
            missing.append("3–5 close references")
        if idea.get("avg_competitor_check") is None:
            missing.append("competitor price evidence")
        if not _present(idea.get("usage_frequency")):
            missing.append("usage_frequency")
        if idea.get("feasible_as_pet_project") is None:
            missing.append("feasibility")
        if idea.get("personal_fit") is None:
            missing.append("personal_fit")
        if missing:
            user_only = set(missing).issubset({"feasibility", "personal_fit"})
            return _need(
                stage,
                "needs_user_input" if user_only else "needs_evidence",
                missing,
                "Fill the selected idea card; research missing market facts before asking the user.",
            )
        return _pass(stage, "Selected idea satisfies idea-readiness contract.", next_action="Run deep competitor/avatar/pain research.")

    if stage == "research_marketing":
        research = state.get("research") or {}
        mc = state.get("marketing_contract") or {}
        missing = []
        if not research.get("competitors"):
            missing.append("research.competitors")
        for key in ["geo", "avatar", "situation", "pain", "solution_steps", "product_type", "primary_benefit"]:
            if not _present(mc.get(key)):
                missing.append(f"marketing_contract.{key}")
        if not _single_value(mc.get("geo")):
            missing.append("single geo")
        if not _single_value(mc.get("avatar")):
            missing.append("single avatar")
        if not _single_value(mc.get("pain")):
            missing.append("single primary pain")
        if not _present(mc.get("price")):
            missing.append("price")
        if not (mc.get("competitor_channels") or research.get("traffic_findings")):
            missing.append("competitor channel research")
        if not mc.get("evidence_ids"):
            missing.append("marketing evidence")
        if missing:
            return _need(stage, "needs_evidence", sorted(set(missing)), "Complete one coherent avatar → situation → pain → solution → benefit contract.")
        return _pass(stage, "Marketing contract is coherent enough for offer design.", next_action="Build one-channel landing/offer brief.")

    if stage == "offer_landing":
        lb = state.get("landing_brief") or {}
        missing = []
        for key in ["channel", "avatar", "primary_cta", "first_screen", "pain_block", "benefit_product_block", "offer_block"]:
            if not _present(lb.get(key)):
                missing.append(key)
        if not lb.get("analytics_events"):
            missing.append("analytics_events")
        if not lb.get("technical_checks"):
            missing.append("technical_checks")
        if missing:
            return _need(stage, "needs_evidence", missing, "Finish the one-avatar, one-channel, one-CTA landing brief and measurement checks.")
        return _pass(stage, "Landing brief contains offer, CTA, mechanism and measurement.", next_action="Select one GTM and calculate experiment economics.")

    if stage == "gtm_planning":
        cp = state.get("channel_plan") or {}
        eco = state.get("economics") or {}
        missing = []
        for key in ["channel", "geo", "conversion_event", "inputs", "current_platform_check"]:
            if not _present(cp.get(key)):
                missing.append(f"channel_plan.{key}")
        if not _present(cp.get("budget")):
            missing.append("channel_plan.budget")
        if eco.get("required_budget") is None and eco.get("max_budget") is None:
            missing.append("economics budget")
        if not _present(eco.get("assumptions")):
            missing.append("economics assumptions")
        if missing:
            return _need(stage, "needs_evidence", missing, "Complete channel-specific inputs, current platform verification and experiment economics.")
        return _pass(stage, "One GTM plan and economics are ready.", next_action="Prepare exact external action and request approval if it can spend/write.")

    if stage == "launch":
        approvals = state.get("approvals", [])
        executable = [a for a in approvals if a.get("status") in {"approved", "executed"}]
        if not executable:
            return _need(
                stage,
                "blocked",
                ["approved action"],
                "Create an exact approval request; do not spend, publish or message without explicit approval.",
            )
        return _pass(stage, "At least one launch action is explicitly approved/executed.", next_action="Execute/read back results and begin lead onboarding.")

    if stage == "lead_onboarding":
        leads = state.get("leads", [])
        if not leads:
            return _need(stage, "needs_evidence", ["lead records"], "Capture real leads and qualification/payment outcomes.")
        qualified = [x for x in leads if x.get("qualified") is True or x.get("status") in {"qualified", "activated", "paid"}]
        if not qualified:
            return _need(stage, "needs_evidence", ["qualified leads"], "Qualify incoming leads before diagnosing demand.")
        return _pass(stage, f"{len(qualified)} qualified lead(s) recorded.", next_action="Record funnel snapshots and a finished iteration.")

    if stage == "iteration_tracking":
        funnels = state.get("funnel_snapshots", [])
        iterations = state.get("iterations", [])
        if not funnels or not iterations:
            return _need(stage, "needs_evidence", ["funnel snapshot", "iteration"], "Finish an iteration with observed reach → clicks → leads → qualified leads → payments.")
        latest = iterations[-1]
        if not _present(latest.get("actual")):
            return _need(stage, "needs_evidence", ["iteration.actual"], "Fill actual results before concluding.")
        return _pass(stage, "Observed funnel and iteration result exist.", next_action="Continue the smallest useful change; consider scale/pivot only after repeated finished iterations.")

    if stage == "scale_or_pivot":
        iterations = state.get("iterations", [])
        finished = [x for x in iterations if _present(x.get("actual")) and _present(x.get("conclusion"))]
        if len(finished) < 4:
            return _need(stage, "needs_evidence", ["four finished iterations or stronger contradictory evidence"], "Do not call channel/idea failure prematurely; finish more iterations.")
        return _pass(stage, f"{len(finished)} finished iterations support a scale/pivot decision.", next_action="Write a decision memo distinguishing channel, offer and idea failure.")

    return GateResult(stage, "blocked", reasons=[f"Unknown stage: {stage}"], next_action="Fix project_state.stage.")
