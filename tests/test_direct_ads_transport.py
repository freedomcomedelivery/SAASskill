import os
import unittest
from unittest.mock import patch

from saasskill.ad_requests import build_ads_read_request
from saasskill.direct_ads_transport import execute_ads_read_request


class DirectAdsTransportTests(unittest.TestCase):
    def test_google_dry_run_does_not_need_credentials(self):
        spec = build_ads_read_request(
            provider="google_ads",
            capability="ads.performance.read",
            account_id="123",
            date_from="2026-09-01",
            date_to="2026-09-30",
        )
        with patch.dict(os.environ, {}, clear=True):
            out = execute_ads_read_request(spec, dry_run=True)
        self.assertEqual(out["status"], "dry_run")
        self.assertFalse(out["integration"]["direct_mode_configured"])

    def test_yandex_live_without_token_fails_before_network(self):
        spec = build_ads_read_request(
            provider="yandex_direct",
            capability="ads.campaigns.read",
            account_id="x",
        )
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                execute_ads_read_request(spec, dry_run=False)

    def test_apple_dry_run_uses_v1(self):
        spec = build_ads_read_request(
            provider="apple_ads",
            capability="ads.campaigns.read",
            account_id="42",
        )
        out = execute_ads_read_request(spec, dry_run=True)
        self.assertIn("/v1/campaigns/query", out["request"]["endpoint"])


if __name__ == "__main__":
    unittest.main()
