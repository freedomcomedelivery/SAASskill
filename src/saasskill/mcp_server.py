from __future__ import annotations

import os
import uuid
from typing import Any

from mcp.server import MCPServer

from .audit import growth_priorities, refresh_audit_report
from .autopilot import ProjectRunner
from .host_executor import HostExecutor
from .orchestrator import Orchestrator
from .providers import ProviderRouter
from .state import ProjectStore, add_evidence, utc_now

mcp = MCPServer("saasskill")


def _store() -> ProjectStore:
    return ProjectStore(os.getenv("SAASSKILL_PROJECT_ROOT", ".saasskill/projects"))


@mcp.tool()
def provider_matrix(available_providers: list[str], preferences: dict[str, list[str]] | None = None) -> dict[str, Any]:
    """Show capability routing across web, Semrush, Ahrefs, Ads, analytics and CRM."""
    return ProviderRouter(available_providers, preferences).matrix()


@mcp.tool()
def project_init(
    name: str,
    project_id: str | None = None,
    workflow: str = "greenfield",
) -> dict[str, Any]:
    """Create a greenfield project or an existing-project audit."""
    return _store().create(name, project_id, workflow)


@mcp.tool()
def project_status(project_id: str) -> dict[str, Any]:
    """Return workflow, stage, gate, readiness and next action."""
    return Orchestrator(_store()).status(project_id)


@mcp.tool()
def project_show(project_id: str) -> dict[str, Any]:
    """Return full project state."""
    return _store().load(project_id)


@mcp.tool()
def project_plan(project_id: str, available_providers: list[str], preferences: dict[str, list[str]] | None = None) -> dict[str, Any]:
    """Create routed provider requests for the current stage."""
    return HostExecutor(_store()).plan(project_id, available_providers=available_providers, preferences=preferences)


@mcp.tool()
def project_tick(
    project_id: str,
    available_providers: list[str],
    preferences: dict[str, list[str]] | None = None,
    auto_advance: bool = True,
) -> dict[str, Any]:
    """Advance passed stages and return the next provider/manual work batch."""
    return ProjectRunner(_store()).tick(
        project_id,
        available_providers=available_providers,
        preferences=preferences,
        auto_advance=auto_advance,
    )


@mcp.tool()
def project_apply_result(project_id: str, result: dict[str, Any]) -> dict[str, Any]:
    """Ingest one result for a previously planned provider request."""
    return HostExecutor(_store()).apply_result(project_id, result)


@mcp.tool()
def project_advance(project_id: str, force: bool = False, reason: str | None = None) -> dict[str, Any]:
    """Advance only when the current stage gate passes, unless a reasoned force override is explicit."""
    state, gate = Orchestrator(_store()).advance(project_id, force=force, reason=reason)
    return {
        "workflow": state.get("workflow"),
        "stage": state["stage"],
        "gate": gate.to_dict(),
        "commercial_readiness": state.get("commercial_readiness"),
        "next_action": state.get("next_action"),
    }


@mcp.tool()
def project_add_evidence(project_id: str, kind: str, claim: str, source_ref: str | None = None, source_title: str | None = None, confidence: float = 0.8) -> dict[str, Any]:
    """Append evidence without changing project stage."""
    store = _store()
    state = store.load(project_id)
    item = add_evidence(state, kind=kind, claim=claim, source_ref=source_ref, source_title=source_title, confidence=confidence)
    store.save(state)
    return item


@mcp.tool()
def audit_refresh(project_id: str) -> dict[str, Any]:
    """Recompute methodology-based audit findings and commercial readiness."""
    store = _store()
    state = store.load(project_id)
    if state.get("workflow") != "existing_project_audit":
        raise ValueError("audit_refresh requires workflow=existing_project_audit")
    report = refresh_audit_report(state)
    store.save(state)
    return report


@mcp.tool()
def audit_growth_priorities(project_id: str) -> list[dict[str, Any]]:
    """Return open audit findings ordered from blocking errors to growth opportunities."""
    state = _store().load(project_id)
    if state.get("workflow") != "existing_project_audit":
        raise ValueError("audit_growth_priorities requires workflow=existing_project_audit")
    return growth_priorities(state)


@mcp.tool()
def approval_create(project_id: str, action_type: str, target: str, summary: str, max_spend: float | None = None, currency: str | None = None, duration: str | None = None, rollback_or_pause: str | None = None) -> dict[str, Any]:
    """Create a pending approval for an external side effect."""
    store = _store()
    state = store.load(project_id)
    item = {
        "id": f"apr_{uuid.uuid4().hex[:10]}",
        "action_type": action_type,
        "target": target,
        "summary": summary,
        "max_spend": max_spend,
        "currency": currency,
        "duration": duration,
        "rollback_or_pause": rollback_or_pause,
        "status": "pending",
        "created_at": utc_now(),
    }
    state.setdefault("approvals", []).append(item)
    store.save(state)
    return item


@mcp.tool()
def approval_decide(project_id: str, approval_id: str, decision: str) -> dict[str, Any]:
    """Approve or reject a pending external action."""
    if decision not in {"approved", "rejected"}:
        raise ValueError("decision must be approved or rejected")
    store = _store()
    state = store.load(project_id)
    item = next((x for x in state.get("approvals", []) if x.get("id") == approval_id), None)
    if item is None:
        raise ValueError(f"approval not found: {approval_id}")
    item["status"] = decision
    item["decided_at"] = utc_now()
    store.save(state)
    return item


def main() -> None:
    transport = os.getenv("SAASSKILL_MCP_TRANSPORT", "stdio")
    if transport == "streamable-http":
        mcp.run(
            transport="streamable-http",
            host=os.getenv("SAASSKILL_MCP_HOST", "127.0.0.1"),
            port=int(os.getenv("SAASSKILL_MCP_PORT", "8000")),
            stateless_http=True,
            json_response=True,
        )
    elif transport == "stdio":
        mcp.run()
    else:
        raise ValueError("SAASSKILL_MCP_TRANSPORT must be stdio or streamable-http")


if __name__ == "__main__":
    main()
