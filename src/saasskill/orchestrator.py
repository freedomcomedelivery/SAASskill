from __future__ import annotations

from copy import deepcopy
from typing import Any

from .gates import GateResult, evaluate_stage
from .state import ProjectStore, STAGES, utc_now


class Orchestrator:
    """Deterministic stage controller."""

    def __init__(self, store: ProjectStore) -> None:
        self.store = store

    def status(self, project_id: str) -> dict[str, Any]:
        state = self.store.load(project_id)
        gate = evaluate_stage(state)
        return {
            "project_id": project_id,
            "name": state.get("name"),
            "stage": state.get("stage"),
            "gate": gate.to_dict(),
            "next_action": gate.next_action or state.get("next_action"),
            "blockers": state.get("blockers", []),
        }

    def advance(self, project_id: str, *, force: bool = False, reason: str | None = None) -> tuple[dict[str, Any], GateResult]:
        state = self.store.load(project_id)
        current = state["stage"]
        gate = evaluate_stage(state, current)
        if not gate.passed and not force:
            state["blockers"] = gate.missing or gate.reasons
            state["next_action"] = gate.next_action
            self.store.save(state)
            return state, gate

        idx = STAGES.index(current)
        if idx == len(STAGES) - 1:
            state["blockers"] = []
            state["next_action"] = gate.next_action
            self.store.save(state)
            return state, gate

        if force and not reason:
            raise ValueError("--force requires a non-empty reason")

        nxt = STAGES[idx + 1]
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
        state.setdefault("action_log", []).append({"type": "artifact_update", "field": field, "at": utc_now()})
        gate = evaluate_stage(state)
        state["blockers"] = gate.missing or gate.reasons
        state["next_action"] = gate.next_action
        self.store.save(state)
        return state
