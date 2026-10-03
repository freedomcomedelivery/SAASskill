import unittest

from saasskill.provider_requests import build_direct_read_spec


class ProviderRequestBuilderTests(unittest.TestCase):
    def test_ahrefs_keyword_spec(self):
        spec=build_direct_read_spec(
            provider="ahrefs", capability="seo.keyword_metrics",
            context={"query":"podcast clips","country":"us","limit":25},
        )
        self.assertEqual(spec["endpoint"],"keywords-explorer/matching-terms")
        self.assertEqual(spec["params"]["keywords"],"podcast clips")

    def test_semrush_domain_spec(self):
        spec=build_direct_read_spec(
            provider="semrush", capability="seo.domain_metrics",
            context={"target":"example.com","country":"us"},
        )
        self.assertEqual(spec["report_type"],"domain_rank")
        self.assertEqual(spec["params"]["domain"],"example.com")

    def test_stripe_spec(self):
        spec=build_direct_read_spec(
            provider="stripe", capability="payments.transactions.read",
            context={"resource":"payment_intents","limit":50},
        )
        self.assertEqual(spec["params"]["limit"],50)

    def test_missing_target_is_not_invented(self):
        with self.assertRaises(ValueError):
            build_direct_read_spec(provider="ahrefs",capability="seo.domain_metrics",context={})


if __name__=="__main__":
    unittest.main()
