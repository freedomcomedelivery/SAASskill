from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Any

AD_CHANNELS = {"search", "meta", "google_display", "rsya", "app_store_asa"}


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def build_campaign_draft(
    *,
    channel_plan: dict[str, Any],
    landing_url: str | None = None,
    creatives: list[dict[str, Any]] | None = None,
    keywords: list[dict[str, Any]] | list[str] | None = None,
    audience: dict[str, Any] | None = None,
    stop_conditions: list[str] | None = None,
) -> dict[str, Any]:
    """Build a provider-neutral paid acquisition draft.

    This is deliberately not a provider API payload. It can be fully tested
    without credentials and later rendered into a provider execution plan.
    """
    cp = deepcopy(channel_plan or {})
    channel = cp.get("channel")
    if channel not in AD_CHANNELS:
        raise ValueError(f"Channel {channel!r} is not a paid ads channel")

    budget = cp.get("budget")
    if isinstance(budget, dict):
        max_spend = budget.get("max_spend") or budget.get("amount")
        currency = budget.get("currency")
        daily_budget = budget.get("daily")
    else:
        max_spend = budget
        currency = cp.get("currency")
        daily_budget = cp.get("daily_budget")

    draft = {
        "id": f"ad_draft_{uuid.uuid4().hex[:10]}",
        "channel": channel,
        "geo": cp.get("geo"),
        "conversion_event": cp.get("conversion_event"),
        "landing_url": landing_url or cp.get("landing_url"),
        "max_spend": max_spend,
        "daily_budget": daily_budget,
        "currency": currency,
        "keywords": deepcopy(keywords or cp.get("keywords") or []),
        "audience": deepcopy(audience or cp.get("audience") or {}),
        "creatives": deepcopy(creatives or cp.get("creatives") or []),
        "tracking": deepcopy(cp.get("tracking") or {}),
        "bid_strategy": cp.get("bid_strategy"),
        "schedule": deepcopy(cp.get("schedule") or {}),
        "stop_conditions": list(stop_conditions or cp.get("stop_conditions") or []),
        "source_channel_plan": cp,
    }
    validation = validate_campaign_draft(draft)
    draft["validation"] = validation
    draft["status"] = "ready_for_provider_render" if validation["ready"] else "incomplete"
    return draft


def validate_campaign_draft(draft: dict[str, Any]) -> dict[str, Any]:
    missing: list[str] = []
    channel = draft.get("channel")
    for key in ("geo", "conversion_event", "max_spend", "currency"):
        if not _present(draft.get(key)):
            missing.append(key)

    if channel != "app_store_asa" and not _present(draft.get("landing_url")):
        missing.append("landing_url")
    if channel in {"search", "app_store_asa"} and not draft.get("keywords"):
        missing.append("keywords")
    if channel in {"meta", "google_display", "rsya"} and not draft.get("creatives"):
        missing.append("creatives")
    if channel in {"meta", "google_display", "rsya"} and not draft.get("audience"):
        missing.append("audience")
    if not draft.get("stop_conditions"):
        missing.append("stop_conditions")

    return {
        "ready": not missing,
        "missing": missing,
        "warnings": [] if draft.get("tracking") else ["tracking configuration is not attached to the draft"],
    }


def render_provider_intent(
    draft: dict[str, Any],
    *,
    provider: str,
    account_id: str,
) -> dict[str, Any]:
    """Render a validated draft into an immutable provider-intent payload.

    The result is suitable for ExecutionManager.prepare(). It is not claimed to
    be a raw provider API request until that provider's account integration has
    rendered/validated it.
    """
    check = validate_campaign_draft(draft)
    if not check["ready"]:
        raise ValueError(f"Campaign draft is incomplete: {check['missing']}")

    allowed = {
        "search": {"google_ads", "yandex_direct"},
        "meta": {"meta_ads"},
        "google_display": {"google_ads"},
        "rsya": {"yandex_direct"},
        "app_store_asa": {"apple_ads"},
    }
    channel = draft["channel"]
    if provider not in allowed[channel]:
        raise ValueError(f"Provider {provider} does not match channel {channel}")

    payload = {
        "draft_id": draft["id"],
        "channel": channel,
        "geo": draft["geo"],
        "conversion_event": draft["conversion_event"],
        "landing_url": draft.get("landing_url"),
        "max_spend": draft["max_spend"],
        "daily_budget": draft.get("daily_budget"),
        "currency": draft["currency"],
        "keywords": deepcopy(draft.get("keywords") or []),
        "audience": deepcopy(draft.get("audience") or {}),
        "creatives": deepcopy(draft.get("creatives") or []),
        "tracking": deepcopy(draft.get("tracking") or {}),
        "bid_strategy": draft.get("bid_strategy"),
        "schedule": deepcopy(draft.get("schedule") or {}),
        "stop_conditions": list(draft.get("stop_conditions") or []),
        "provider_render_status": "needs_account_level_render_and_validation",
    }
    return {
        "provider": provider,
        "operation": "campaign.create",
        "target": str(account_id),
        "payload": payload,
        "max_spend": draft["max_spend"],
        "currency": draft["currency"],
        "side_effect": True,
    }
