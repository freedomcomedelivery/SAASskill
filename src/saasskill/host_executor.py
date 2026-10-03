from __future__ import annotations

import uuid
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .gates import evaluate_stage
from .providers import ProviderRouter
from .state import ProjectStore, add_evidence, utc_now
from .workplan import build_work_queue


PATCHABLE_ROOTS = {
    "personal_concept",
    "markets",
    "ideas",
    "selected_idea_id",
    "research",
    "marketing_contract",
    "landing_brief",
    "economics",
    "channel_plan",
    "leads",
    "funnel_snapshots",
    "iterations",
}


@dataclass(slots=True)
class ToolRequest:
    request_id: str
    work_key: str
    kind: str
    description: str
    requested_capability: str
    effective_capability: str
    provider: str | None
    degraded: bool
    side_effect: bool
    approval_required: bool
    payload: dict[str, Any]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "work_key": self.work_key,
            "kind": self.kind,
            "description": self.description,
            "requested_capability": self.requested_capability,
            "effective_capability": self.effective_capability,
            "provider": self.provider,
            "degraded": self.degraded,
            "side_effect": self.side_effect,
            "approval_required": self.approval_required,
            "payload": self.payload,
            "created_at": self.created_at,
        }


class HostExecutor:
    """Create provider-neutral tool requests and ingest host results."""

    def __init__(self, store: ProjectStore) -> None:
        self.store = store

    def plan(
        self,
        project_id: str,
        *,
        available_providers: list[str],
        preferences: dict[str, list[str]] | None = None,
    ) -> dict[str, Any]:
        state = self.store.load(project_id)
        router = ProviderRouter(available_providers, preferences)
        work = build_work_queue(state)
        requests: list[dict[str, Any]] = []
        unresolved: list[dict[str, Any]] = []
        manual: list[dict[str, Any]] = []

        for item in work:
            capability = item.get("capability")
            if not capability:
                manual.append(item)
                continue

            route = router.resolve(capability)
            req = ToolRequest(
                request_id=f"req_{uuid.uuid4().hex[:10]}",
                work_key=item["key"],
                kind=item["kind"],
                description=item["description"],
                requested_capability=route.requested_capability,
                effective_capability=route.effective_capability,
                provider=route.provider,
                degraded=route.degraded,
                side_effect=bool(item.get("side_effect")),
                approval_required=bool(item.get("side_effect")),
                payload={
                    "project_id": project_id,
                    "stage": state.get("stage"),
                    "work_key": item["key"],
                    "description": item["description"],
                    "state_context": {
                        "name": state.get("name"),
                        "selected_idea_id": state.get("selected_idea_id"),
                        "channel_plan": state.get("channel_plan"),
                    },
                },
                created_at=utc_now(),
            ).to_dict()

            if route.resolved:
                requests.append(req)
            else:
                req["route_reason"] = route.reason
                unresolved.append(req)

        return {
            "project_id": project_id,
            "stage": state.get("stage"),
            "gate": evaluate_stage(state).to_dict(),
            "available_providers": sorted(set(available_providers)),
            "requests": requests,
            "manual_work": manual,
            "unresolved": unresolved,
        }

    def apply_result(self, project_id: str, result: dict[str, Any]) -> dict[str, Any]:
        state = self.store.load(project_id)
        status = result.get("status")
        if status not in {"ok", "error", "skipped"}:
            raise ValueError("result.status must be ok, error or skipped")
        if not result.get("request_id"):
            raise ValueError("result.request_id is required")

        provider = result.get("provider")
        capability = result.get("capability")
        degraded = bool(result.get("degraded"))

        state.setdefault("tool_results", []).append(deepcopy(result))

        for ev in result.get("evidence", []) or []:
            notes = ev.get("notes")
            provenance = f"provider={provider}; capability={capability}; degraded={degraded}"
            notes = f"{notes}; {provenance}" if notes else provenance
            add_evidence(
                state,
                kind=ev.get("kind", "fact"),
                claim=ev["claim"],
                source_ref=ev.get("source_ref"),
                source_title=ev.get("source_title"),
                confidence=float(ev.get("confidence", 0.8)),
                supports=ev.get("supports", []),
                formula=ev.get("formula"),
                assumptions=ev.get("assumptions", []),
                notes=notes,
            )

        patch = result.get("state_patch") or {}
        forbidden = sorted(set(patch) - PATCHABLE_ROOTS)
        if forbidden:
            raise PermissionError(f"Host result cannot patch protected roots: {', '.join(forbidden)}")
        for key, value in patch.items():
            state[key] = deepcopy(value)

        state.setdefault("action_log", []).append({
            "type": "tool_result",
            "request_id": result["request_id"],
            "provider": provider,
            "capability": capability,
            "status": status,
            "at": utc_now(),
        })

        gate = evaluate_stage(state)
        state["blockers"] = gate.missing or gate.reasons
        state["next_action"] = gate.next_action
        self.store.save(state)
        return {
            "project_id": project_id,
            "stage": state.get("stage"),
            "gate": gate.to_dict(),
            "evidence_count": len(state.get("evidence", [])),
            "next_action": state.get("next_action"),
        }
