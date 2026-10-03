import unittest

from saasskill.ads import (
    normalize_apple_ads_result,
    normalize_google_ads_result,
    normalize_meta_ads_result,
    normalize_yandex_direct_result,
)


class AdsNormalizerTests(unittest.TestCase):
    def test_google_ads_micros(self):
        result = normalize_google_ads_result(
            request_id="r1",
            payload=[{
                "campaign": {"id": "1", "name": "Search"},
                "metrics": {
                    "impressions": 1000, "clicks": 100, "cost_micros": 25000000,
                    "conversions": 10, "conversions_value": 100,
                },
            }],
            context={"account_id": "123", "currency": "USD"},
        )
        totals = result["data"]["totals"]
        self.assertEqual(totals["spend"], 25)
        self.assertEqual(totals["cpc"], 0.25)
        self.assertEqual(result["provider"], "google_ads")

    def test_meta_actions(self):
        result = normalize_meta_ads_result(
            request_id="r2",
            payload={"data": [{
                "campaign_id": "c1", "impressions": "1000", "clicks": "50", "spend": "20.50",
                "actions": [{"action_type": "lead", "value": "8"}, {"action_type": "purchase", "value": "2"}],
                "action_values": [{"action_type": "purchase", "value": "120"}],
            }]},
        )
        row = result["data"]["rows"][0]
        self.assertEqual(row["leads"], 8)
        self.assertEqual(row["purchases"], 2)
        self.assertEqual(row["revenue"], 120)

    def test_yandex_tsv(self):
        tsv = "CampaignId\tCampaignName\tImpressions\tClicks\tCost\tConversions\n1\tTest\t2000\t100\t300\t4\n"
        result = normalize_yandex_direct_result(request_id="r3", payload=tsv, context={"currency": "RUB"})
        self.assertEqual(result["data"]["totals"]["impressions"], 2000)
        self.assertEqual(result["data"]["totals"]["conversions"], 4)

    def test_apple_report(self):
        result = normalize_apple_ads_result(
            request_id="r4",
            payload={"data": [{
                "metadata": {"campaignId": 7, "campaignName": "ASA"},
                "metrics": {"impressions": 500, "taps": 25, "installs": 5, "spend": {"amount": "10.50"}},
            }]},
            context={"currency": "USD"},
        )
        self.assertEqual(result["data"]["totals"]["clicks"], 25)
        self.assertEqual(result["data"]["totals"]["conversions"], 5)
        self.assertEqual(result["data"]["totals"]["spend"], 10.5)


if __name__ == "__main__":
    unittest.main()
