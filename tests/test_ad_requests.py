import unittest

from saasskill.ad_requests import build_ads_read_request


class AdsRequestBuilderTests(unittest.TestCase):
    def test_google_performance_gaql(self):
        req = build_ads_read_request(
            provider="google_ads", capability="ads.performance.read",
            account_id="123", date_from="2026-09-01", date_to="2026-09-30",
        )
        self.assertEqual(req["tool"], "search")
        self.assertIn("metrics.cost_micros", req["arguments"]["query"])
        self.assertIn("BETWEEN '2026-09-01' AND '2026-09-30'", req["arguments"]["query"])

    def test_meta_campaign_inventory(self):
        req = build_ads_read_request(
            provider="meta_ads", capability="ads.campaigns.read", account_id="act_1",
        )
        self.assertEqual(req["operation"], "AdAccount.get_campaigns")

    def test_yandex_report_v501(self):
        req = build_ads_read_request(
            provider="yandex_direct", capability="ads.performance.read",
            account_id="login", date_from="2026-09-01", date_to="2026-09-30",
        )
        self.assertIn("/v501/reports", req["endpoint"])
        self.assertEqual(req["arguments"]["params"]["ReportType"], "CAMPAIGN_PERFORMANCE_REPORT")

    def test_apple_uses_platform_v1(self):
        req = build_ads_read_request(
            provider="apple_ads", capability="ads.performance.read",
            account_id="42", date_from="2026-09-01", date_to="2026-09-30",
        )
        self.assertEqual(req["endpoint"], "https://api.ads.apple.com/v1/reports/apps/campaigns/query")
        self.assertIn("adAccountId=42", req["headers"]["X-AP-Context"])


if __name__ == "__main__":
    unittest.main()
