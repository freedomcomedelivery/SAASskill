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
    "audit_snapshot",
    "audit_report",
    "growth_plan",
    "selected_growth_action_id",
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
    provider_candidates: list[str] | None
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
            "provider_candidates": self.provider_candidates,
            "degraded": self.degraded,
            "side_effect": self.side_effect,
            "approval_required": self.approval_required,
            "payload": self.payload,
            "created_at": self.created_at,
        }


def _deep_merge(dst: dict[str, Any], src: dict[str, Any]) -> dict[str, Any]:
    for key, value in src.items():
        if isinstance(value, dict) and isinstance(dst.get(key), dict):
            _deep_merge(dst[key], value)
        else:
            dst[key] = deepcopy(value)
    return dst


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

            candidates = item.get("provider_candidates")
            route = router.resolve(capability, candidates=candidates)
            req = ToolRequest(
                request_id=f"req_{uuid.uuid4().hex[:10]}",
                work_key=item["key"],
                kind=item["kind"],
                description=item["description"],
                requested_capability=route.requested_capability,
                effective_capability=route.effective_capability,
                provider=route.provider,
                provider_candidates=candidates,
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
                        "workflow": state.get("workflow"),
                        "audit_snapshot": state.get("audit_snapshot"),
                        "commercial_readiness": state.get("commercial_readiness"),
                    },
                },
                created_at=utc_now(),
            ).to_dict()

            if route.resolved:
                requests.append(req)
            else:
                req["route_reason"] = route.reason
                unresolved.append(req)

        pending = state.setdefault("pending_tool_requests", [])
        for req in requests:
            pending[:] = [
                old for old in pending
                if not (
                    old.get("status") == "pending"
                    and old.get("work_key") == req["work_key"]
                    and old.get("payload", {}).get("stage") == state.get("stage")
                )
            ]
            pending.append({**deepcopy(req), "status": "pending"})
        self.store.save(state)

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
        request_id = result.get("request_id")
        if not request_id:
            raise ValueError("result.request_id is required")

        pending = next(
            (x for x in state.get("pending_tool_requests", []) if x.get("request_id") == request_id),
            None,
        )
        if pending is None:
            raise PermissionError(f"Unknown or unplanned request_id: {request_id}")
        if pending.get("status") != "pending":
            raise PermissionError(f"Request is not pending: {request_id}")

        expected_provider = pending.get("provider")
        expected_capability = pending.get("effective_capability")
        supplied_provider = result.get("provider")
        supplied_capability = result.get("capability")
        if supplied_provider is not None and supplied_provider != expected_provider:
            raise PermissionError(
                f"Provider mismatch for {request_id}: expected {expected_provider}, got {supplied_provider}"
            )
        if supplied_capability is not None and supplied_capability != expected_capability:
            raise PermissionError(
                f"Capability mismatch for {request_id}: expected {expected_capability}, got {supplied_capability}"
            )

        if pending.get("side_effect"):
            raise PermissionError(
                "Side-effect ToolResult is not accepted through HostExecutor; use execution_plans "
                "(prepare → dry-run → exact plan-bound approval → dispatch → complete)."
            )

        provider = expected_provider
        capability = expected_capability
        degraded = bool(pending.get("degraded"))

        normalized = deepcopy(result)
        normalized["provider"] = provider
        normalized["capability"] = capability
        normalized["degraded"] = degraded
        normalized["observed_at"] = normalized.get("observed_at") or utc_now()
        state.setdefault("tool_results", []).append(normalized)

        added_evidence_ids: list[str] = []
        for ev in normalized.get("evidence", []) or []:
            notes = ev.get("notes")
            provenance = f"provider={provider}; capability={capability}; degraded={degraded}"
            notes = f"{notes}; {provenance}" if notes else provenance
            added = add_evidence(
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
            added_evidence_ids.append(added["id"])

        patch = normalized.get("state_patch") or {}
        forbidden = sorted(set(patch) - PATCHABLE_ROOTS)
        if forbidden:
            raise PermissionError(f"Host result cannot patch protected roots: {', '.join(forbidden)}")
        for key, value in patch.items():
            state[key] = deepcopy(value)

        merge_patch = normalized.get("state_merge_patch") or {}
        forbidden_merge = sorted(set(merge_patch) - PATCHABLE_ROOTS)
        if forbidden_merge:
            raise PermissionError(f"Host result cannot merge protected roots: {', '.join(forbidden_merge)}")
        for key, value in merge_patch.items():
            if not isinstance(value, dict):
                state[key] = deepcopy(value)
                continue
            current = state.get(key)
            if not isinstance(current, dict):
                current = {}
                state[key] = current
            _deep_merge(current, value)

        pending["status"] = "completed" if status == "ok" else status
        pending["completed_at"] = utc_now()

        state.setdefault("action_log", []).append({
            "type": "tool_result",
            "request_id": request_id,
            "provider": provider,
            "capability": capability,
            "status": status,
            "at": utc_now(),
        })

        if state.get("workflow") == "existing_project_audit":
            from .audit import refresh_audit_report
            refresh_audit_report(state)
        gate = evaluate_stage(state)
        state["blockers"] = gate.missing or gate.reasons
        state["next_action"] = gate.next_action
        self.store.save(state)
        return {
            "project_id": project_id,
            "stage": state.get("stage"),
            "gate": gate.to_dict(),
            "evidence_count": len(state.get("evidence", [])),
            "evidence_ids_added": added_evidence_ids,
            "next_action": state.get("next_action"),
        }
