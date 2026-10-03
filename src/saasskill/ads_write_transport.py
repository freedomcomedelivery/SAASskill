from __future__ import annotations

import json
import os
import urllib.request
from typing import Any


def _ensure_dispatch(dispatch: dict[str, Any]) -> None:
    if not dispatch.get("apply") or dispatch.get("dry_run"):
        raise PermissionError("Live ads write requires an approved apply dispatch from ExecutionManager")
    if not dispatch.get("approval_id") or not dispatch.get("plan_digest"):
        raise PermissionError("Dispatch is not bound to an approval/digest")


def _http_json(url: str, *, headers: dict[str, str], body: Any, timeout: float) -> Any:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers={**headers, "Content-Type": "application/json; charset=utf-8"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode("utf-8", errors="replace")
    return json.loads(raw) if raw else {}


def execute_ads_write_dispatch(dispatch: dict[str, Any], *, dry_run: bool = True, timeout: float = 30.0) -> dict[str, Any]:
    """Execute a small, auditable set of ad-account mutations.

    Complex campaign creation remains host/MCP-managed until integration tests are
    run against real test accounts. This function covers pause/resume/status/budget
    operations that can be represented unambiguously.
    """
    if dry_run:
        return {"status": "dry_run", "dispatch": dispatch}
    _ensure_dispatch(dispatch)

    provider = dispatch["provider"]
    operation = dispatch["operation"]
    target = str(dispatch["target"])
    payload = dict(dispatch.get("payload") or {})

    if provider == "google_ads":
        from google.ads.googleads.client import GoogleAdsClient
        from google.api_core import protobuf_helpers

        client = GoogleAdsClient.load_from_env()
        customer_id = str(payload.get("customer_id") or "").replace("-", "")
        if not customer_id:
            raise ValueError("Google Ads write requires payload.customer_id")
        if operation == "campaign.status":
            campaign_service = client.get_service("CampaignService")
            op = client.get_type("CampaignOperation")
            campaign = op.update
            campaign.resource_name = campaign_service.campaign_path(customer_id, target)
            status = str(payload["status"]).upper()
            if status not in {"ENABLED", "PAUSED"}:
                raise ValueError("Google Ads campaign.status supports ENABLED or PAUSED")
            campaign.status = getattr(client.enums.CampaignStatusEnum, status)
            client.copy_from(
                op.update_mask,
                protobuf_helpers.field_mask(None, campaign._pb),
            )
            result = campaign_service.mutate_campaigns(customer_id=customer_id, operations=[op])
            return {"status": "ok", "provider": provider, "operation": operation, "result": str(result)}
        raise NotImplementedError("Google Ads direct writes currently support campaign.status only")

    if provider == "meta_ads":
        from facebook_business.api import FacebookAdsApi
        from facebook_business.adobjects.campaign import Campaign

        FacebookAdsApi.init(os.environ["META_APP_ID"], os.environ["META_APP_SECRET"], os.environ["META_ACCESS_TOKEN"])
        if operation == "campaign.status":
            status = str(payload["status"]).upper()
            if status not in {"ACTIVE", "PAUSED"}:
                raise ValueError("Meta campaign.status supports ACTIVE or PAUSED")
            result = Campaign(target).api_update(params={"status": status})
            return {"status": "ok", "provider": provider, "operation": operation, "result": dict(result)}
        raise NotImplementedError("Meta direct writes currently support campaign.status only")

    if provider == "yandex_direct":
        token = os.getenv("YANDEX_DIRECT_TOKEN") or os.getenv("YANDEX_ACCESS_TOKEN")
        headers = {"Authorization": "Bearer " + str(token), "Accept-Language": "en"}
        if os.getenv("YANDEX_CLIENT_LOGIN"):
            headers["Client-Login"] = os.environ["YANDEX_CLIENT_LOGIN"]
        method = {"campaign.pause": "suspend", "campaign.resume": "resume"}.get(operation)
        if method:
            body = {"method": method, "params": {"SelectionCriteria": {"Ids": [int(target)]}}}
            result = _http_json("https://api.direct.yandex.com/json/v5/campaigns", headers=headers, body=body, timeout=timeout)
            return {"status": "ok", "provider": provider, "operation": operation, "result": result}
        raise NotImplementedError("Yandex Direct writes currently support campaign.pause/campaign.resume only")

    if provider in {"apple_ads", "pipeboard", "ads"}:
        raise NotImplementedError(f"{provider} live write remains host/MCP-managed until account-level integration tests")

    raise ValueError(f"Unsupported ads write provider: {provider}")
