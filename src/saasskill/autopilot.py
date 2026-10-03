from __future__ import annotations

from typing import Any

from .audit import refresh_audit_report
from .gates import evaluate_stage
from .host_executor import HostExecutor
from .orchestrator import Orchestrator
from .state import ProjectStore


class ProjectRunner:
    """One deterministic host-loop tick.

    The runner does not call external providers itself. It advances passed stages,
    returns already-pending requests, or plans the next routed batch for the host.
    """

    def __init__(self, store: ProjectStore) -> None:
        self.store = store
        self.orchestrator = Orchestrator(store)
        self.executor = HostExecutor(store)

    def tick(
        self,
        project_id: str,
        *,
        available_providers: list[str],
        preferences: dict[str, list[str]] | None = None,
        auto_advance: bool = True,
    ) -> dict[str, Any]:
        state = self.store.load(project_id)
        if state.get("workflow") == "existing_project_audit":
            refresh_audit_report(state)
            self.store.save(state)

        current_pending = [
            x for x in state.get("pending_tool_requests", [])
            if x.get("status") == "pending"
            and x.get("payload", {}).get("stage") == state.get("stage")
        ]
        if current_pending:
            return {
                "project_id": project_id,
                "workflow": state.get("workflow"),
                "stage": state.get("stage"),
                "status": "awaiting_provider_results",
                "requests": current_pending,
                "gate": evaluate_stage(state).to_dict(),
            }

        gate = evaluate_stage(state)
        advanced = None
        if gate.passed and auto_advance:
            before = state.get("stage")
            state, _ = self.orchestrator.advance(project_id)
            if state.get("stage") != before:
                advanced = {"from": before, "to": state.get("stage")}
                gate = evaluate_stage(state)

        plan = self.executor.plan(
            project_id,
            available_providers=available_providers,
            preferences=preferences,
        )
        return {
            "project_id": project_id,
            "workflow": state.get("workflow"),
            "stage": plan["stage"],
            "status": "planned",
            "advanced": advanced,
            "gate": plan["gate"],
            "commercial_readiness": self.store.load(project_id).get("commercial_readiness"),
            "requests": plan["requests"],
            "manual_work": plan["manual_work"],
            "unresolved": plan["unresolved"],
        }
