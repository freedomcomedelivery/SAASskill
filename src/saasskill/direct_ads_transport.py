from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

from .integration_status import integration_status


def _require_direct(provider: str) -> None:
    status = integration_status(provider)
    if not status.get("direct_mode_configured"):
        missing_groups = [
            g.get("missing", []) for g in status.get("credential_groups", []) if not g.get("configured")
        ]
        raise RuntimeError(
            f"{provider} direct mode is not configured. Missing one credential group from: {missing_groups}"
        )


def _jsonable_google_row(row: Any) -> dict[str, Any]:
    try:
        from google.protobuf.json_format import MessageToDict
        pb = getattr(row, "_pb", row)
        return MessageToDict(pb, preserving_proto_field_name=True)
    except Exception:
        return {"repr": str(row)}


def _google(spec: dict[str, Any]) -> Any:
    _require_direct("google_ads")
    from google.ads.googleads.client import GoogleAdsClient

    client = GoogleAdsClient.load_from_env()
    tool = spec.get("tool")
    args = spec.get("arguments") or {}
    if tool == "list_accessible_customers":
        service = client.get_service("CustomerService")
        response = service.list_accessible_customers()
        return [{"id": str(name).split("/")[-1], "resource_name": str(name)} for name in response.resource_names]
    if tool == "search":
        service = client.get_service("GoogleAdsService")
        response = service.search(customer_id=str(args["customer_id"]), query=args["query"])
        return [_jsonable_google_row(row) for row in response]
    raise ValueError(f"Unsupported Google Ads direct read tool: {tool}")


def _meta(spec: dict[str, Any]) -> Any:
    _require_direct("meta_ads")
    from facebook_business.api import FacebookAdsApi
    from facebook_business.adobjects.adaccount import AdAccount
    from facebook_business.adobjects.user import User

    FacebookAdsApi.init(
        os.environ["META_APP_ID"],
        os.environ["META_APP_SECRET"],
        os.environ["META_ACCESS_TOKEN"],
    )
    operation = spec.get("operation")
    args = spec.get("arguments") or {}
    if operation == "User.get_ad_accounts":
        rows = User("me").get_ad_accounts(fields=["id", "name", "account_status", "currency"])
    elif operation == "AdAccount.get_campaigns":
        rows = AdAccount(args["account_id"]).get_campaigns(fields=args.get("fields", []))
    elif operation == "AdAccount.get_insights":
        params = {"level": args.get("level", "campaign"), "time_range": args["time_range"]}
        rows = AdAccount(args["account_id"]).get_insights(fields=args.get("fields", []), params=params)
    else:
        raise ValueError(f"Unsupported Meta Ads direct read operation: {operation}")
    return [dict(row) for row in rows]


def _http_json(
    url: str,
    *,
    method: str,
    headers: dict[str, str],
    body: Any = None,
    timeout: float = 30.0,
) -> Any:
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers = {**headers, "Content-Type": "application/json; charset=utf-8"}
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read()
        content_type = response.headers.get("Content-Type", "")
    text = raw.decode("utf-8", errors="replace")
    if "json" in content_type.lower():
        return json.loads(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _yandex(spec: dict[str, Any], timeout: float) -> Any:
    _require_direct("yandex_direct")
    token = os.getenv("YANDEX_DIRECT_TOKEN") or os.getenv("YANDEX_ACCESS_TOKEN")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept-Language": "en",
    }
    client_login = os.getenv("YANDEX_CLIENT_LOGIN")
    if client_login:
        headers["Client-Login"] = client_login

    if spec.get("endpoint"):
        headers["returnMoneyInMicros"] = "false"
        return _http_json(
            spec["endpoint"],
            method="POST",
            headers=headers,
            body=spec.get("arguments") or {},
            timeout=timeout,
        )

    service = str(spec["service"]).lower()
    endpoint = f"https://api.direct.yandex.com/json/v5/{service}"
    body = {"method": spec["method"], "params": spec.get("arguments") or {}}
    return _http_json(endpoint, method="POST", headers=headers, body=body, timeout=timeout)


def _apple(spec: dict[str, Any], timeout: float) -> Any:
    _require_direct("apple_ads")
    token = os.getenv("APPLE_ADS_ACCESS_TOKEN")
    if not token:
        raise RuntimeError(
            "Direct Apple Ads executor currently requires APPLE_ADS_ACCESS_TOKEN. "
            "OAuth client-secret generation/token exchange remains host-managed."
        )
    headers = {"Authorization": f"Bearer {token}", **(spec.get("headers") or {})}
    return _http_json(
        spec["endpoint"],
        method=spec.get("method", "GET"),
        headers=headers,
        body=spec.get("body") if spec.get("method", "GET") != "GET" else None,
        timeout=timeout,
    )


def execute_ads_read_request(
    spec: dict[str, Any],
    *,
    dry_run: bool = True,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Execute a previously built read spec. Defaults to dry-run.

    This executor is read-only; advertising writes must use ExecutionManager and
    plan-bound approval.
    """
    provider = spec.get("provider")
    if dry_run:
        return {
            "status": "dry_run",
            "provider": provider,
            "request": spec,
            "integration": integration_status(provider) if provider in {"google_ads", "meta_ads", "yandex_direct", "apple_ads"} else None,
        }

    if provider == "google_ads":
        payload = _google(spec)
    elif provider == "meta_ads":
        payload = _meta(spec)
    elif provider == "yandex_direct":
        payload = _yandex(spec, timeout)
    elif provider == "apple_ads":
        payload = _apple(spec, timeout)
    else:
        raise ValueError(
            f"Direct executor does not execute provider {provider}; use the host/MCP transport for this provider."
        )
    return {"status": "ok", "provider": provider, "request": spec, "payload": payload}
