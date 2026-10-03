from __future__ import annotations

import json
import re
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

GREENFIELD_STAGES = [
    "intake",
    "personal_concept",
    "market_discovery",
    "idea_generation",
    "idea_selection",
    "research_marketing",
    "offer_landing",
    "gtm_planning",
    "launch",
    "lead_onboarding",
    "iteration_tracking",
    "scale_or_pivot",
]

AUDIT_STAGES = [
    "audit_intake",
    "audit_snapshot",
    "audit_market_positioning",
    "audit_offer_landing",
    "audit_acquisition",
    "audit_funnel_sales",
    "audit_economics",
    "audit_growth_plan",
    "audit_execution",
    "audit_iteration",
    "audit_growth_loop",
]

STAGES_BY_WORKFLOW = {
    "greenfield": GREENFIELD_STAGES,
    "existing_project_audit": AUDIT_STAGES,
}
STAGES = GREENFIELD_STAGES + AUDIT_STAGES


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def slugify(value: str) -> str:
    value = re.sub(r"[^\w\-]+", "-", value.strip().lower(), flags=re.UNICODE)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "project"


def workflow_stages(workflow: str) -> list[str]:
    try:
        return STAGES_BY_WORKFLOW[workflow]
    except KeyError as exc:
        raise ValueError(f"Unknown workflow: {workflow}") from exc


def infer_workflow(stage: str) -> str:
    if stage in AUDIT_STAGES:
        return "existing_project_audit"
    return "greenfield"


def new_project_state(
    name: str,
    project_id: str | None = None,
    workflow: str = "greenfield",
) -> dict[str, Any]:
    stages = workflow_stages(workflow)
    project_id = project_id or f"{slugify(name)}-{uuid.uuid4().hex[:8]}"
    now = utc_now()
    initial_stage = stages[0]
    state = {
        "project_id": project_id,
        "name": name,
        "workflow": workflow,
        "stage": initial_stage,
        "runtime_version": "1.4.0",
        "personal_concept": None,
        "markets": [],
        "ideas": [],
        "selected_idea_id": None,
        "research": None,
        "marketing_contract": None,
        "landing_brief": None,
        "economics": None,
        "channel_plan": None,
        "evidence": [],
        "approvals": [],
        "leads": [],
        "funnel_snapshots": [],
        "iterations": [],
        "blockers": [],
        "next_action": None,
        "stage_history": [{
            "from": None,
            "to": initial_stage,
            "at": now,
            "reason": "project_created",
            "forced": False,
        }],
        "action_log": [],
        "pending_tool_requests": [],
        "tool_results": [],
        "audit_snapshot": None,
        "audit_report": None,
        "growth_plan": None,
        "selected_growth_action_id": None,
        "commercial_readiness": "unknown",
        "created_at": now,
        "updated_at": now,
    }
    if workflow == "greenfield":
        state["next_action"] = "Define project scope and constraints."
    else:
        state["next_action"] = "Collect the existing product URL/assets, current offer, target, channels and any available metrics."
    return state


class ProjectStore:
    """Filesystem persistence: <root>/<project_id>/state.json."""

    def __init__(self, root: str | Path = ".saasskill/projects") -> None:
        self.root = Path(root)

    def _dir(self, project_id: str) -> Path:
        return self.root / project_id

    def path(self, project_id: str) -> Path:
        return self._dir(project_id) / "state.json"

    def create(
        self,
        name: str,
        project_id: str | None = None,
        workflow: str = "greenfield",
    ) -> dict[str, Any]:
        state = new_project_state(name=name, project_id=project_id, workflow=workflow)
        target = self.path(state["project_id"])
        if target.exists():
            raise FileExistsError(f"Project already exists: {state['project_id']}")
        self.save(state)
        return state

    def load(self, project_id: str) -> dict[str, Any]:
        target = self.path(project_id)
        if not target.exists():
            raise FileNotFoundError(f"Unknown project: {project_id}")
        state = json.loads(target.read_text(encoding="utf-8"))
        if not state.get("workflow"):
            state["workflow"] = infer_workflow(state.get("stage", "intake"))
        return state

    def save(self, state: dict[str, Any]) -> Path:
        project_id = state.get("project_id")
        if not project_id:
            raise ValueError("project_id is required")
        workflow = state.get("workflow") or infer_workflow(state.get("stage", "intake"))
        stages = workflow_stages(workflow)
        if state.get("stage") not in stages:
            raise ValueError(f"Stage {state.get('stage')!r} does not belong to workflow {workflow!r}")
        state = deepcopy(state)
        state["workflow"] = workflow
        state["runtime_version"] = "1.4.0"
        state["updated_at"] = utc_now()
        target = self.path(project_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(target)
        return target

    def list_projects(self) -> list[str]:
        if not self.root.exists():
            return []
        return sorted(p.name for p in self.root.iterdir() if (p / "state.json").exists())


def add_evidence(
    state: dict[str, Any],
    *,
    kind: str,
    claim: str,
    source_ref: str | None = None,
    source_title: str | None = None,
    confidence: float = 0.8,
    supports: Iterable[str] = (),
    formula: str | None = None,
    assumptions: Iterable[str] = (),
    notes: str | None = None,
) -> dict[str, Any]:
    allowed = {"fact", "estimate", "hypothesis", "course_heuristic", "user_constraint"}
    if kind not in allowed:
        raise ValueError(f"Invalid evidence kind: {kind}")
    if not 0 <= confidence <= 1:
        raise ValueError("confidence must be between 0 and 1")
    item = {
        "id": f"ev_{uuid.uuid4().hex[:10]}",
        "kind": kind,
        "claim": claim,
        "source_ref": source_ref,
        "source_title": source_title,
        "observed_at": utc_now(),
        "confidence": confidence,
        "formula": formula,
        "assumptions": list(assumptions),
        "supports": list(supports),
        "notes": notes,
    }
    state.setdefault("evidence", []).append(item)
    return item


def dotted_set(state: dict[str, Any], path: str, value: Any) -> None:
    parts = [p for p in path.split(".") if p]
    if not parts:
        raise ValueError("field path is empty")
    cur: Any = state
    for part in parts[:-1]:
        if isinstance(cur, list):
            cur = cur[int(part)]
        else:
            cur = cur.setdefault(part, {})
    last = parts[-1]
    if isinstance(cur, list):
        cur[int(last)] = value
    else:
        cur[last] = value
