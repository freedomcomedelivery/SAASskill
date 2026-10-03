import unittest

from saasskill.ads_drafts import build_campaign_draft, render_provider_intent


class AdsDraftTests(unittest.TestCase):
    def test_search_draft_can_be_validated_without_credentials(self):
        draft=build_campaign_draft(
            channel_plan={
                "channel":"search","geo":"US","conversion_event":"paid",
                "budget":{"max_spend":500,"currency":"USD"},
                "tracking":{"event":"purchase"},
            },
            landing_url="https://example.com",
            keywords=["buy ai clips","podcast clip service"],
            stop_conditions=["pause at USD 500 max spend"],
        )
        self.assertEqual(draft["status"],"ready_for_provider_render")
        intent=render_provider_intent(draft,provider="google_ads",account_id="123")
        self.assertEqual(intent["operation"],"campaign.create")
        self.assertTrue(intent["side_effect"])

    def test_meta_requires_creatives_and_audience(self):
        draft=build_campaign_draft(
            channel_plan={
                "channel":"meta","geo":"US","conversion_event":"lead",
                "budget":{"max_spend":200,"currency":"USD"},
            },
            landing_url="https://example.com",
            stop_conditions=["pause at USD 200"],
        )
        self.assertEqual(draft["status"],"incomplete")
        self.assertIn("creatives",draft["validation"]["missing"])
        self.assertIn("audience",draft["validation"]["missing"])

    def test_provider_channel_mismatch_is_rejected(self):
        draft=build_campaign_draft(
            channel_plan={"channel":"search","geo":"US","conversion_event":"paid","budget":{"max_spend":100,"currency":"USD"}},
            landing_url="https://example.com",keywords=["buy x"],stop_conditions=["cap"],
        )
        with self.assertRaises(ValueError):
            render_provider_intent(draft,provider="meta_ads",account_id="1")


if __name__=="__main__":
    unittest.main()
