from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Any

from .state import utc_now

SUPPORTED_AD_PROVIDERS = {"google_ads", "meta_ads", "yandex_direct", "apple_ads", "pipeboard", "ads"}

PROVIDER_TRANSPORT = {
    "google_ads": "google-ads-mcp-or-google-ads-python",
    "meta_ads": "facebook-business-sdk-or-mcp",
    "yandex_direct": "yandex-direct-api-v501-or-mcp",
    "apple_ads": "apple-ads-platform-api-v1",
    "pipeboard": "pipeboard-mcp",
    "ads": "host-ads-provider",
}


class ExecutionManager:
    """Store dry-run-first external action plans and bind approvals to exact plan IDs."""

    def prepare(
        self,
        state: dict[str, Any],
        *,
        provider: str,
        operation: str,
        target: str,
        payload: dict[str, Any],
        max_spend: float | None = None,
        currency: str | None = None,
        side_effect: bool = True,
    ) -> dict[str, Any]:
        if provider not in SUPPORTED_AD_PROVIDERS:
            raise ValueError(f"Unsupported ad provider: {provider}")
        plan = {
            "id": f"plan_{uuid.uuid4().hex[:10]}",
            "provider": provider,
            "transport": PROVIDER_TRANSPORT[provider],
            "operation": operation,
            "target": target,
            "payload": deepcopy(payload),
            "max_spend": max_spend,
            "currency": currency,
            "side_effect": side_effect,
            "status": "prepared",
            "created_at": utc_now(),
        }
        state.setdefault("execution_plans", []).append(plan)
        return plan

    def get(self, state: dict[str, Any], plan_id: str) -> dict[str, Any]:
        plan = next((x for x in state.get("execution_plans", []) if x.get("id") == plan_id), None)
        if plan is None:
            raise ValueError(f"Execution plan not found: {plan_id}")
        return plan

    def validate_approval(self, plan: dict[str, Any], approval: dict[str, Any]) -> None:
        if approval.get("status") != "approved":
            raise PermissionError("Approval must be approved")
        if approval.get("plan_id") != plan.get("id"):
            raise PermissionError("Approval is not bound to this execution plan")
        approved_cap = approval.get("max_spend")
        requested_cap = plan.get("max_spend")
        if approved_cap is not None and requested_cap is not None and float(requested_cap) > float(approved_cap):
            raise PermissionError("Execution plan spend cap exceeds approved cap")
        approved_currency = approval.get("currency")
        if approved_currency and plan.get("currency") and approved_currency != plan.get("currency"):
            raise PermissionError("Execution plan currency does not match approval")

    def dispatch(
        self,
        state: dict[str, Any],
        *,
        plan_id: str,
        approval_id: str | None = None,
        apply: bool = False,
    ) -> dict[str, Any]:
        plan = self.get(state, plan_id)
        approval = None
        if apply and plan.get("side_effect"):
            if not approval_id:
                raise PermissionError("Side-effect dispatch requires approval_id")
            approval = next((x for x in state.get("approvals", []) if x.get("id") == approval_id), None)
            if approval is None:
                raise PermissionError(f"Approval not found: {approval_id}")
            self.validate_approval(plan, approval)

        dispatch = {
            "plan_id": plan_id,
            "provider": plan["provider"],
            "transport": plan["transport"],
            "operation": plan["operation"],
            "target": plan["target"],
            "payload": deepcopy(plan["payload"]),
            "max_spend": plan.get("max_spend"),
            "currency": plan.get("currency"),
            "apply": bool(apply),
            "dry_run": not bool(apply),
            "approval_id": approval_id if apply else None,
            "created_at": utc_now(),
        }
        if apply:
            plan["status"] = "dispatched"
            plan["dispatched_at"] = utc_now()
            plan["approval_id"] = approval_id
        return dispatch

    def complete(self, state: dict[str, Any], *, plan_id: str, result: dict[str, Any]) -> dict[str, Any]:
        plan = self.get(state, plan_id)
        status = result.get("status")
        if status not in {"ok", "error"}:
            raise ValueError("Execution result status must be ok or error")
        plan["status"] = "executed" if status == "ok" else "failed"
        plan["completed_at"] = utc_now()
        plan["result"] = deepcopy(result)
        state.setdefault("action_log", []).append({
            "type": "execution_plan_result",
            "plan_id": plan_id,
            "provider": plan.get("provider"),
            "operation": plan.get("operation"),
            "status": plan["status"],
            "at": utc_now(),
        })
        return plan
