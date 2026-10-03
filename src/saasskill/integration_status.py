from __future__ import annotations

import importlib.util
import os
from typing import Any


INTEGRATIONS = {
    "ahrefs": {
        "preferred": "official_remote_mcp",
        "endpoint": "https://api.ahrefs.com/mcp/mcp",
        "direct_env_any": [["AHREFS_API_KEY"]],
    },
    "semrush": {
        "preferred": "official_remote_mcp",
        "endpoint": "https://mcp.semrush.com/v2/mcp",
        "direct_env_any": [["SEMRUSH_API_KEY"]],
    },
    "google_ads": {
        "preferred": "official_mcp_for_reads + official_python_sdk_for_custom_writes",
        "package": "google.ads.googleads",
        "direct_env_any": [
            ["GOOGLE_ADS_CONFIGURATION_FILE_PATH"],
            ["GOOGLE_ADS_DEVELOPER_TOKEN", "GOOGLE_ADS_CLIENT_ID", "GOOGLE_ADS_CLIENT_SECRET", "GOOGLE_ADS_REFRESH_TOKEN"],
        ],
    },
    "meta_ads": {
        "preferred": "official_facebook_business_sdk_or_connected_mcp",
        "package": "facebook_business",
        "direct_env_any": [["META_APP_ID", "META_APP_SECRET", "META_ACCESS_TOKEN"]],
    },
    "yandex_direct": {
        "preferred": "official_direct_api_or_yandex-direct-metrica-mcp",
        "direct_env_any": [["YANDEX_ACCESS_TOKEN"], ["YANDEX_DIRECT_TOKEN"]],
    },
    "apple_ads": {
        "preferred": "official_platform_api_v1",
        "package_optional": "asa_api_client",
        "direct_env_any": [
            ["APPLE_ADS_ACCESS_TOKEN"],
            ["APPLE_ADS_CLIENT_ID", "APPLE_ADS_TEAM_ID", "APPLE_ADS_KEY_ID", "APPLE_ADS_PRIVATE_KEY_PATH"],
        ],
    },
    "camoufox": {
        "preferred": "local_optional_dependency",
        "package": "camoufox",
        "direct_env_any": [[]],
    },
}


def _package_available(name: str | None) -> bool | None:
    if not name:
        return None
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ModuleNotFoundError, AttributeError):
        return False


def integration_status(name: str) -> dict[str, Any]:
    try:
        spec = INTEGRATIONS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown integration: {name}") from exc
    package_name = spec.get("package") or spec.get("package_optional")
    package_required = "package" in spec
    package_available = _package_available(package_name)

    groups = spec.get("direct_env_any", [])
    group_status = []
    configured = False
    for group in groups:
        missing = [key for key in group if not os.getenv(key)]
        ok = not missing
        configured = configured or ok
        group_status.append({"keys": group, "configured": ok, "missing": missing})

    if package_required and package_available is False:
        configured = False

    return {
        "name": name,
        "preferred": spec.get("preferred"),
        "endpoint": spec.get("endpoint"),
        "package": package_name,
        "package_required_for_direct_mode": package_required,
        "package_available": package_available,
        "direct_mode_configured": configured,
        "credential_groups": group_status,
        "note": "Remote MCP/OAuth connectivity is host-managed and cannot be inferred from local environment variables.",
    }


def integration_matrix() -> dict[str, dict[str, Any]]:
    return {name: integration_status(name) for name in sorted(INTEGRATIONS)}
