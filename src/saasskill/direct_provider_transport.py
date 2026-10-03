from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Any

from .integration_status import integration_status


def _require(provider: str) -> None:
    status = integration_status(provider)
    if not status.get("direct_mode_configured"):
        missing = [g.get("missing", []) for g in status.get("credential_groups", []) if not g.get("configured")]
        raise RuntimeError(f"{provider} direct mode is not configured; missing one credential group from {missing}")


def _request(url: str, *, method: str = "GET", headers: dict[str, str] | None = None, body: Any = None, timeout: float = 30.0) -> Any:
    data = None
    hdrs = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, method=method, headers=hdrs)
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


def execute_direct_read(provider: str, spec: dict[str, Any], *, dry_run: bool = True, timeout: float = 30.0) -> dict[str, Any]:
    """Execute a whitelisted read-only provider spec. Defaults to dry-run."""
    if dry_run:
        return {"status": "dry_run", "provider": provider, "spec": spec, "integration": integration_status(provider)}
    _require(provider)

    if provider == "semrush":
        params = dict(spec.get("params") or {})
        params["key"] = os.environ["SEMRUSH_API_KEY"]
        url = "https://api.semrush.com/?" + urllib.parse.urlencode(params)
        payload = _request(url, timeout=timeout)

    elif provider == "ahrefs":
        endpoint = str(spec.get("endpoint") or "").strip("/")
        if not endpoint or ".." in endpoint:
            raise ValueError("Ahrefs endpoint is required")
        params = urllib.parse.urlencode(spec.get("params") or {}, doseq=True)
        url = "https://api.ahrefs.com/v3/" + endpoint + (("?" + params) if params else "")
        payload = _request(url, headers={"Authorization": "Bearer " + os.environ["AHREFS_API_KEY"]}, timeout=timeout)

    elif provider == "posthog":
        project_id = os.environ["POSTHOG_PROJECT_ID"]
        base = str(os.getenv("POSTHOG_BASE_URL") or "https://us.posthog.com").rstrip("/")
        if urllib.parse.urlparse(base).hostname not in {"us.posthog.com", "eu.posthog.com"} and not os.getenv("POSTHOG_ALLOW_CUSTOM_BASE"):
            raise PermissionError("Custom PostHog base URL requires POSTHOG_ALLOW_CUSTOM_BASE")
        payload = _request(
            f"{base}/api/projects/{project_id}/query/",
            method="POST",
            headers={"Authorization": "Bearer " + os.environ["POSTHOG_API_KEY"]},
            body=spec.get("body") or {},
            timeout=timeout,
        )

    elif provider == "yandex_metrica":
        params = dict(spec.get("params") or {})
        params.setdefault("ids", os.environ["YANDEX_METRICA_COUNTER_ID"])
        url = "https://api-metrika.yandex.net/stat/v1/data?" + urllib.parse.urlencode(params, doseq=True)
        payload = _request(url, headers={"Authorization": "OAuth " + os.environ["YANDEX_ACCESS_TOKEN"]}, timeout=timeout)

    elif provider == "hubspot":
        path = str(spec.get("path") or "/crm/v3/objects/contacts").strip()
        if not path.startswith("/crm/") or ".." in path:
            raise PermissionError("HubSpot direct reader is restricted to /crm/* paths")
        params = urllib.parse.urlencode(spec.get("params") or {}, doseq=True)
        url = "https://api.hubapi.com" + path + (("?" + params) if params else "")
        payload = _request(url, headers={"Authorization": "Bearer " + os.environ["HUBSPOT_ACCESS_TOKEN"]}, timeout=timeout)

    elif provider == "stripe":
        resource = str(spec.get("resource") or "payment_intents")
        if resource not in {"payment_intents", "charges", "invoices"}:
            raise PermissionError("Stripe direct reader supports payment_intents, charges or invoices")
        params = urllib.parse.urlencode(spec.get("params") or {"limit": 100}, doseq=True)
        payload = _request(
            f"https://api.stripe.com/v1/{resource}?{params}",
            headers={"Authorization": "Bearer " + os.environ["STRIPE_API_KEY"]},
            timeout=timeout,
        )

    elif provider == "ga4":
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest

        property_id = str(spec.get("property_id") or os.environ["GA4_PROPERTY_ID"])
        request = RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=[Dimension(name=x) for x in spec.get("dimensions", [])],
            metrics=[Metric(name=x) for x in spec.get("metrics", [])],
            date_ranges=[DateRange(start_date=x["start_date"], end_date=x["end_date"]) for x in spec.get("date_ranges", [])],
            limit=int(spec.get("limit", 10000)),
        )
        response = BetaAnalyticsDataClient().run_report(request)
        payload = {
            "dimensionHeaders": [{"name": x.name} for x in response.dimension_headers],
            "metricHeaders": [{"name": x.name} for x in response.metric_headers],
            "rows": [
                {
                    "dimensionValues": [{"value": x.value} for x in row.dimension_values],
                    "metricValues": [{"value": x.value} for x in row.metric_values],
                }
                for row in response.rows
            ],
        }
    else:
        raise ValueError(f"Unsupported direct read provider: {provider}")

    return {"status": "ok", "provider": provider, "spec": spec, "payload": payload}
