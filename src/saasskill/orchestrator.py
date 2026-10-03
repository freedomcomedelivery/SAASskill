from __future__ import annotations

from copy import deepcopy
from typing import Any

from .audit import refresh_audit_report
from .gates import GateResult, evaluate_stage
from .state import ProjectStore, utc_now, workflow_stages


class Orchestrator:
    """Deterministic stage controller for greenfield and existing-project audit workflows."""

    def __init__(self, store: ProjectStore) -> None:
        self.store = store

    def status(self, project_id: str) -> dict[str, Any]:
        state = self.store.load(project_id)
        if state.get("workflow") == "existing_project_audit":
            refresh_audit_report(state)
            self.store.save(state)
        gate = evaluate_stage(state)
        return {
            "project_id": project_id,
            "name": state.get("name"),
            "workflow": state.get("workflow"),
            "stage": state.get("stage"),
            "commercial_readiness": state.get("commercial_readiness"),
            "gate": gate.to_dict(),
            "next_action": gate.next_action or state.get("next_action"),
            "blockers": state.get("blockers", []),
        }

    def advance(self, project_id: str, *, force: bool = False, reason: str | None = None) -> tuple[dict[str, Any], GateResult]:
        state = self.store.load(project_id)
        if state.get("workflow") == "existing_project_audit":
            refresh_audit_report(state)
        current = state["stage"]
        gate = evaluate_stage(state, current)
        if not gate.passed and not force:
            state["blockers"] = gate.missing or gate.reasons
            state["next_action"] = gate.next_action
            self.store.save(state)
            return state, gate

        stages = workflow_stages(state.get("workflow", "greenfield"))
        idx = stages.index(current)
        if idx == len(stages) - 1:
            state["blockers"] = []
            state["next_action"] = gate.next_action
            self.store.save(state)
            return state, gate

        if force and not reason:
            raise ValueError("--force requires a non-empty reason")

        nxt = stages[idx + 1]
        state["stage"] = nxt
        state["blockers"] = []
        state["next_action"] = evaluate_stage(state, nxt).next_action
        state.setdefault("stage_history", []).append({
            "from": current,
            "to": nxt,
            "at": utc_now(),
            "reason": reason or "gate_passed",
            "forced": bool(force),
            "gate_status": gate.status,
        })
        state.setdefault("action_log", []).append({
            "type": "stage_transition",
            "from": current,
            "to": nxt,
            "at": utc_now(),
            "forced": bool(force),
            "reason": reason or "gate_passed",
        })
        self.store.save(state)
        return state, gate

    def set_artifact(self, project_id: str, field: str, value: Any) -> dict[str, Any]:
        state = self.store.load(project_id)
        state[field] = deepcopy(value)
        if state.get("workflow") == "existing_project_audit":
            refresh_audit_report(state)
        state.setdefault("action_log", []).append({"type": "artifact_update", "field": field, "at": utc_now()})
        gate = evaluate_stage(state)
        state["blockers"] = gate.missing or gate.reasons
        state["next_action"] = gate.next_action
        self.store.save(state)
        return state
