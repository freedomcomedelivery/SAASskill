from __future__ import annotations

import os
import uuid
from typing import Any

from mcp.server.mcpserver import MCPServer

from .audit import build_growth_plan, growth_priorities, mark_audit_section, refresh_audit_report, update_growth_action
from .autopilot import ProjectRunner
from .ahrefs import normalize_ahrefs_result
from .ads import normalize_ads_result
from .ad_requests import build_ads_read_request
from .direct_ads_transport import execute_ads_read_request
from .direct_provider_transport import execute_direct_read
from .provider_requests import build_direct_read_spec
from .ads_write_transport import execute_ads_write_dispatch
from .camoufox_parser import extract_html_snapshot, fetch_public_page
from .camofox_rest import fetch_surface as fetch_camofox_rest_surface
from .parser_normalizer import normalize_public_page_result
from .executors import ExecutionManager, execution_plan_digest
from .integration_status import integration_matrix, integration_status
from .analytics import normalize_analytics_result
from .crm import normalize_crm_result
from .payments import normalize_payments_result
from .semrush import normalize_semrush_result
from .host_executor import HostExecutor
from .orchestrator import Orchestrator
from .providers import ProviderRouter
from .state import ProjectStore, add_evidence, utc_now

mcp = MCPServer("saasskill")


def _store() -> ProjectStore:
    return ProjectStore(os.getenv("SAASSKILL_PROJECT_ROOT", ".saasskill/projects"))


@mcp.tool()
def integration_check(name: str | None = None) -> dict[str, Any]:
    """Show local direct-mode readiness without exposing secret values."""
    return integration_status(name) if name else integration_matrix()


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
def provider_normalize_ahrefs(
    request_id: str,
    endpoint: str,
    payload: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize an official Ahrefs MCP/API response into a SAASskill ToolResult."""
    return normalize_ahrefs_result(
        request_id=request_id,
        endpoint=endpoint,
        payload=payload,
        context=context,
    )


@mcp.tool()
def provider_normalize_semrush(
    request_id: str,
    report_type: str,
    payload: Any,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize Semrush MCP/API/CSV data into a SAASskill ToolResult."""
    return normalize_semrush_result(request_id=request_id, report_type=report_type, payload=payload, context=context)


@mcp.tool()
def provider_normalize_ads(
    provider: str,
    request_id: str,
    payload: Any,
    context: dict[str, Any] | None = None,
    capability: str = "ads.performance.read",
) -> dict[str, Any]:
    """Normalize accounts, campaigns or performance data from an ads provider."""
    return normalize_ads_result(
        provider=provider,
        request_id=request_id,
        payload=payload,
        context=context,
        capability=capability,
    )


@mcp.tool()
def ads_build_read_request(
    provider: str,
    capability: str,
    account_id: str,
    date_from: str | None = None,
    date_to: str | None = None,
    level: str = "campaign",
) -> dict[str, Any]:
    """Build a credential-free concrete read request for an advertising provider."""
    return build_ads_read_request(
        provider=provider,
        capability=capability,
        account_id=account_id,
        date_from=date_from,
        date_to=date_to,
        level=level,
    )


@mcp.tool()
def ads_execute_read_request(
    spec: dict[str, Any],
    dry_run: bool = True,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Execute a concrete ads read request directly; defaults to dry-run and never performs writes."""
    return execute_ads_read_request(spec, dry_run=dry_run, timeout=timeout)


@mcp.tool()
def provider_build_direct_read_spec(
    provider: str,
    capability: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Build a direct-provider request spec without credentials or network access."""
    return build_direct_read_spec(provider=provider, capability=capability, context=context)


@mcp.tool()
def project_build_pending_direct_spec(
    project_id: str,
    request_id: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a provider-specific direct read spec from a pending SAASskill request."""
    _store_obj, state, pending = _pending_request(project_id, request_id)
    provider = pending.get("provider")
    merged = _ingest_context(state, pending, context)
    return build_direct_read_spec(
        provider=provider,
        capability=pending.get("effective_capability"),
        context=merged,
    )


@mcp.tool()
def project_execute_pending_auto(
    project_id: str,
    request_id: str,
    context: dict[str, Any] | None = None,
    dry_run: bool = True,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Build the direct spec, execute it, normalize and ingest in one call."""
    _store_obj, state, pending = _pending_request(project_id, request_id)
    provider = pending.get("provider")
    supported = {"ahrefs", "semrush", "posthog", "ga4", "yandex_metrica", "hubspot", "stripe"}
    if provider not in supported:
        raise ValueError(f"Automatic direct execution is not available for provider {provider}")
    spec = build_direct_read_spec(
        provider=provider,
        capability=pending.get("effective_capability"),
        context=_ingest_context(state, pending, context),
    )
    return project_execute_pending_direct(
        project_id=project_id,
        request_id=request_id,
        spec=spec,
        dry_run=dry_run,
        timeout=timeout,
    )


@mcp.tool()
def provider_execute_direct_read(
    provider: str,
    spec: dict[str, Any],
    dry_run: bool = True,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Execute a whitelisted direct read for Ahrefs/Semrush/analytics/CRM/payments; defaults to dry-run."""
    return execute_direct_read(provider, spec, dry_run=dry_run, timeout=timeout)


@mcp.tool()
def parser_fetch_public_rest(
    url: str,
    timeout: float = 30.0,
    allowed_domains: list[str] | None = None,
) -> dict[str, Any]:
    """Fetch and parse a public page through a separately running camofox-browser REST server."""
    return fetch_camofox_rest_surface(
        url,
        timeout=timeout,
        allowed_domains=set(allowed_domains or []) or None,
    )


@mcp.tool()
def ads_execute_write_dispatch(
    dispatch: dict[str, Any],
    dry_run: bool = True,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Execute a previously approved ads dispatch; defaults to dry-run."""
    return execute_ads_write_dispatch(dispatch, dry_run=dry_run, timeout=timeout)


@mcp.tool()
def parser_extract_html(html: str, url: str | None = None) -> dict[str, Any]:
    """Extract commercial surface data from already-fetched public HTML."""
    return extract_html_snapshot(html, url=url)


@mcp.tool()
def parser_fetch_public(url: str, timeout_ms: int = 30000, allowed_domains: list[str] | None = None) -> dict[str, Any]:
    """Fetch a public page with Camoufox; no login/CAPTCHA bypass is attempted."""
    return fetch_public_page(url, timeout_ms=timeout_ms, allowed_domains=set(allowed_domains or []) or None)


@mcp.tool()
def ads_prepare_execution(
    project_id: str,
    provider: str,
    operation: str,
    target: str,
    payload: dict[str, Any],
    max_spend: float | None = None,
    currency: str | None = None,
    related_action_id: str | None = None,
) -> dict[str, Any]:
    """Store an exact dry-run-first advertising execution plan."""
    store = _store()
    state = store.load(project_id)
    plan = ExecutionManager().prepare(
        state,
        provider=provider,
        operation=operation,
        target=target,
        payload=payload,
        max_spend=max_spend,
        currency=currency,
        side_effect=True,
        related_action_id=related_action_id,
    )
    store.save(state)
    return plan


@mcp.tool()
def ads_dispatch_execution(
    project_id: str,
    plan_id: str,
    approval_id: str | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    """Render/dispatch a stored execution plan. apply=true requires exact plan-bound approval."""
    store = _store()
    state = store.load(project_id)
    dispatch = ExecutionManager().dispatch(state, plan_id=plan_id, approval_id=approval_id, apply=apply)
    store.save(state)
    return dispatch


@mcp.tool()
def ads_complete_execution(project_id: str, plan_id: str, result: dict[str, Any]) -> dict[str, Any]:
    """Store the provider result after the host executes a dispatched plan."""
    store = _store()
    state = store.load(project_id)
    plan = ExecutionManager().complete(state, plan_id=plan_id, result=result)
    store.save(state)
    return plan


def _pending_request(project_id: str, request_id: str) -> tuple[ProjectStore, dict[str, Any], dict[str, Any]]:
    store = _store()
    state = store.load(project_id)
    pending = next(
        (x for x in state.get("pending_tool_requests", []) if x.get("request_id") == request_id and x.get("status") == "pending"),
        None,
    )
    if pending is None:
        raise ValueError(f"Pending request not found: {request_id}")
    return store, state, pending


def _ingest_context(state: dict[str, Any], pending: dict[str, Any], extra: dict[str, Any] | None = None) -> dict[str, Any]:
    ctx = dict((pending.get("payload") or {}).get("state_context") or {})
    ctx.update({
        "workflow": state.get("workflow"),
        "stage": state.get("stage"),
        "work_key": pending.get("work_key"),
    })
    ctx.update(extra or {})
    return ctx


@mcp.tool()
def project_ingest_ahrefs(
    project_id: str,
    request_id: str,
    endpoint: str,
    payload: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize and apply an Ahrefs result for an existing pending request."""
    store, state, pending = _pending_request(project_id, request_id)
    if pending.get("provider") != "ahrefs":
        raise ValueError(f"Request {request_id} is routed to {pending.get('provider')}, not ahrefs")
    result = normalize_ahrefs_result(
        request_id=request_id,
        endpoint=endpoint,
        payload=payload,
        context=_ingest_context(state, pending, context),
    )
    return HostExecutor(store).apply_result(project_id, result)


@mcp.tool()
def project_ingest_semrush(
    project_id: str,
    request_id: str,
    report_type: str,
    payload: Any,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize and apply a Semrush result for an existing pending request."""
    store, state, pending = _pending_request(project_id, request_id)
    if pending.get("provider") != "semrush":
        raise ValueError(f"Request {request_id} is routed to {pending.get('provider')}, not semrush")
    result = normalize_semrush_result(
        request_id=request_id,
        report_type=report_type,
        payload=payload,
        context=_ingest_context(state, pending, context),
    )
    return HostExecutor(store).apply_result(project_id, result)


@mcp.tool()
def project_ingest_ads(
    project_id: str,
    request_id: str,
    payload: Any,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize and apply a concrete ad-provider read result."""
    store, state, pending = _pending_request(project_id, request_id)
    provider = pending.get("provider")
    capability = pending.get("effective_capability")
    if provider not in {"google_ads", "meta_ads", "yandex_direct", "apple_ads"}:
        raise ValueError(f"Automatic ads ingestion is not available for provider {provider}")
    result = normalize_ads_result(
        provider=provider,
        request_id=request_id,
        payload=payload,
        context=_ingest_context(state, pending, context),
        capability=capability,
    )
    return HostExecutor(store).apply_result(project_id, result)


@mcp.tool()
def project_ingest_analytics(
    project_id: str,
    request_id: str,
    payload: Any,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize and apply analytics funnel data for a pending request."""
    store, state, pending = _pending_request(project_id, request_id)
    provider = pending.get("provider")
    if provider not in {"posthog", "ga4", "yandex_metrica", "analytics"}:
        raise ValueError(f"Automatic analytics ingestion is not available for provider {provider}")
    result = normalize_analytics_result(
        provider=provider,
        request_id=request_id,
        payload=payload,
        context=_ingest_context(state, pending, context),
    )
    return HostExecutor(store).apply_result(project_id, result)


@mcp.tool()
def project_ingest_crm(
    project_id: str,
    request_id: str,
    payload: Any,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize and apply CRM lead/deal data for a pending request."""
    store, state, pending = _pending_request(project_id, request_id)
    provider = pending.get("provider")
    if provider not in {"hubspot", "crm"}:
        raise ValueError(f"Automatic CRM ingestion is not available for provider {provider}")
    result = normalize_crm_result(
        provider=provider,
        request_id=request_id,
        payload=payload,
        context=_ingest_context(state, pending, context),
    )
    return HostExecutor(store).apply_result(project_id, result)


@mcp.tool()
def project_ingest_payments(
    project_id: str,
    request_id: str,
    payload: Any,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize and apply verified payment records for a pending request."""
    store, state, pending = _pending_request(project_id, request_id)
    provider = pending.get("provider")
    if provider not in {"stripe", "payments"}:
        raise ValueError(f"Automatic payments ingestion is not available for provider {provider}")
    result = normalize_payments_result(
        provider=provider,
        request_id=request_id,
        payload=payload,
        context=_ingest_context(state, pending, context),
    )
    return HostExecutor(store).apply_result(project_id, result)


@mcp.tool()
def project_ingest_public_page(
    project_id: str,
    request_id: str,
    snapshot: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize and apply a public-page/browser parse result."""
    store, state, pending = _pending_request(project_id, request_id)
    effective = pending.get("effective_capability")
    if effective not in {"web.browser_parse", "web.fetch"}:
        raise ValueError(f"Request {request_id} is not a page-fetch/browser request")
    result = normalize_public_page_result(
        request_id=request_id,
        snapshot=snapshot,
        context=_ingest_context(state, pending, context),
        provider=pending.get("provider") or "web",
        capability=effective,
    )
    return HostExecutor(store).apply_result(project_id, result)


@mcp.tool()
def project_execute_pending_direct(
    project_id: str,
    request_id: str,
    spec: dict[str, Any],
    dry_run: bool = True,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Execute + normalize + ingest a pending non-ads direct-provider request."""
    store, state, pending = _pending_request(project_id, request_id)
    provider = pending.get("provider")
    supported = {"ahrefs", "semrush", "posthog", "ga4", "yandex_metrica", "hubspot", "stripe"}
    if provider not in supported:
        raise ValueError(f"Direct pending execution is not available for provider {provider}")
    executed = execute_direct_read(provider, spec, dry_run=dry_run, timeout=timeout)
    if dry_run:
        return executed
    payload = executed["payload"]
    context = _ingest_context(state, pending, spec.get("context"))

    if provider == "ahrefs":
        result = normalize_ahrefs_result(
            request_id=request_id,
            endpoint=spec["endpoint"],
            payload=payload,
            context=context,
        )
    elif provider == "semrush":
        report_type = spec.get("report_type") or (spec.get("params") or {}).get("type")
        if not report_type:
            raise ValueError("Semrush direct spec requires report_type or params.type")
        result = normalize_semrush_result(
            request_id=request_id,
            report_type=report_type,
            payload=payload,
            context=context,
        )
    elif provider in {"posthog", "ga4", "yandex_metrica"}:
        result = normalize_analytics_result(
            provider=provider,
            request_id=request_id,
            payload=payload,
            context=context,
        )
    elif provider == "hubspot":
        result = normalize_crm_result(
            provider=provider,
            request_id=request_id,
            payload=payload,
            context=context,
        )
    else:
        result = normalize_payments_result(
            provider=provider,
            request_id=request_id,
            payload=payload,
            context=context,
        )
    return HostExecutor(store).apply_result(project_id, result)


@mcp.tool()
def project_execute_pending_ads_direct(
    project_id: str,
    request_id: str,
    spec: dict[str, Any],
    dry_run: bool = True,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Execute + normalize + ingest a pending advertising read request."""
    store, state, pending = _pending_request(project_id, request_id)
    provider = pending.get("provider")
    if provider not in {"google_ads", "meta_ads", "yandex_direct", "apple_ads"}:
        raise ValueError(f"Direct ads execution is not available for provider {provider}")
    if spec.get("provider") != provider:
        raise ValueError(f"Spec provider {spec.get('provider')} does not match pending provider {provider}")
    executed = execute_ads_read_request(spec, dry_run=dry_run, timeout=timeout)
    if dry_run:
        return executed
    result = normalize_ads_result(
        provider=provider,
        request_id=request_id,
        payload=executed["payload"],
        context=_ingest_context(state, pending),
        capability=pending.get("effective_capability"),
    )
    return HostExecutor(store).apply_result(project_id, result)


@mcp.tool()
def project_execute_pending_public_rest(
    project_id: str,
    request_id: str,
    url: str,
    allowed_domains: list[str] | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Fetch via camofox-browser REST, normalize the public commercial surface and ingest it."""
    store, state, pending = _pending_request(project_id, request_id)
    effective = pending.get("effective_capability")
    if effective not in {"web.browser_parse", "web.fetch"}:
        raise ValueError(f"Request {request_id} is not a browser/public-page request")
    if pending.get("provider") not in {"camoufox", "web"}:
        raise ValueError(f"Request {request_id} is routed to {pending.get('provider')}, not a browser provider")
    surface = fetch_camofox_rest_surface(
        url,
        timeout=timeout,
        allowed_domains=set(allowed_domains or []) or None,
    )
    result = normalize_public_page_result(
        request_id=request_id,
        snapshot=surface,
        context=_ingest_context(state, pending),
        provider=pending.get("provider") or "camoufox",
        capability=effective,
    )
    return HostExecutor(store).apply_result(project_id, result)


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
def audit_mark_section(project_id: str, section: str, summary: str, evidence_ids: list[str]) -> dict[str, Any]:
    """Mark one audit section complete after the host has collected/synthesized its evidence."""
    store = _store()
    state = store.load(project_id)
    if state.get("workflow") != "existing_project_audit":
        raise ValueError("audit_mark_section requires workflow=existing_project_audit")
    out = mark_audit_section(state, section, summary=summary, evidence_ids=evidence_ids)
    store.save(state)
    return out


@mcp.tool()
def audit_build_growth_plan(project_id: str) -> dict[str, Any]:
    """Build prioritized repair/growth actions from current open findings and readiness."""
    store = _store()
    state = store.load(project_id)
    if state.get("workflow") != "existing_project_audit":
        raise ValueError("audit_build_growth_plan requires workflow=existing_project_audit")
    plan = build_growth_plan(state)
    store.save(state)
    return plan


@mcp.tool()
def audit_select_growth_action(project_id: str, action_id: str) -> dict[str, Any]:
    """Select the next growth action from the generated plan."""
    store = _store()
    state = store.load(project_id)
    actions = (state.get("growth_plan") or {}).get("actions") or []
    action = next((x for x in actions if x.get("id") == action_id), None)
    if action is None:
        raise ValueError(f"Growth action not found: {action_id}")
    state["selected_growth_action_id"] = action_id
    store.save(state)
    return action


@mcp.tool()
def audit_update_growth_action(project_id: str, action_id: str, status: str) -> dict[str, Any]:
    """Update execution status for one growth action."""
    store = _store()
    state = store.load(project_id)
    action = update_growth_action(state, action_id, status)
    store.save(state)
    return action


@mcp.tool()
def project_set_artifact(project_id: str, field: str, value: Any) -> dict[str, Any]:
    """Set one project artifact without allowing direct stage mutation."""
    allowed = {
        "personal_concept", "markets", "ideas", "selected_idea_id", "research",
        "marketing_contract", "landing_brief", "economics", "channel_plan",
        "leads", "funnel_snapshots", "iterations", "audit_snapshot",
        "audit_report", "growth_plan", "selected_growth_action_id",
    }
    if field not in allowed:
        raise PermissionError(f"Artifact field is protected or unknown: {field}")
    return Orchestrator(_store()).set_artifact(project_id, field, value)


@mcp.tool()
def approval_create(project_id: str, action_type: str, target: str, summary: str, max_spend: float | None = None, currency: str | None = None, duration: str | None = None, rollback_or_pause: str | None = None, plan_id: str | None = None) -> dict[str, Any]:
    """Create a pending approval for an external side effect."""
    store = _store()
    state = store.load(project_id)
    if plan_id is not None:
        plan = next((x for x in state.get("execution_plans", []) if x.get("id") == plan_id), None)
        if plan is None:
            raise ValueError(f"Execution plan not found: {plan_id}")
        if max_spend is None:
            max_spend = plan.get("max_spend")
        if currency is None:
            currency = plan.get("currency")
        plan_digest = execution_plan_digest(plan)
    else:
        plan_digest = None
    item = {
        "id": f"apr_{uuid.uuid4().hex[:10]}",
        "action_type": action_type,
        "target": target,
        "summary": summary,
        "max_spend": max_spend,
        "currency": currency,
        "duration": duration,
        "rollback_or_pause": rollback_or_pause,
        "plan_id": plan_id,
        "plan_digest": plan_digest,
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
