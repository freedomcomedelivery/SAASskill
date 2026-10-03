#!/usr/bin/env python3
from saasskill.ad_requests import build_ads_read_request
from saasskill.direct_ads_transport import execute_ads_read_request
from saasskill.integration_status import integration_matrix

print("Integration matrix:")
for name, status in integration_matrix().items():
    print(name, "direct=", status["direct_mode_configured"], "package=", status.get("package_available"))

print("\nCredential-free ads read specs:")
for provider in ("google_ads", "meta_ads", "yandex_direct", "apple_ads"):
    spec = build_ads_read_request(
        provider=provider,
        capability="ads.performance.read",
        account_id="demo",
        date_from="2026-09-01",
        date_to="2026-09-30",
    )
    out = execute_ads_read_request(spec, dry_run=True)
    print(provider, out["status"])
