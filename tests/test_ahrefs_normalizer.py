import unittest

from saasskill.ahrefs import normalize_ahrefs_result


class AhrefsNormalizerTests(unittest.TestCase):
    def test_matching_terms_normalization(self):
        result = normalize_ahrefs_result(
            request_id="req_1",
            endpoint="keywords-explorer/matching-terms",
            payload={
                "keywords": [
                    {"keyword": "ai clips", "volume": 1000, "cpc": 250, "difficulty": 25},
                    {"keyword": "podcast shorts", "volume": 500, "cpc": 150, "difficulty": 18},
                ]
            },
            context={"country": "US", "query": "podcast clips"},
        )
        self.assertEqual(result["provider"], "ahrefs")
        self.assertEqual(result["capability"], "seo.keyword_metrics")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(result["evidence"]), 1)
        self.assertIn("1,500", result["evidence"][0]["claim"])
        self.assertIn("USD 2.00", result["evidence"][0]["claim"])

    def test_domain_rating_normalization(self):
        result = normalize_ahrefs_result(
            request_id="req_2",
            endpoint="/v3/site-explorer/domain-rating",
            payload={"domain_rating": {"ahrefs_rank": 1234, "domain_rating": 67.5}},
            context={"target": "example.com"},
        )
        self.assertEqual(result["capability"], "seo.domain_metrics")
        self.assertIn("DR 67.5", result["evidence"][0]["claim"])

    def test_organic_competitors_normalization(self):
        result = normalize_ahrefs_result(
            request_id="req_3",
            endpoint="site-explorer/organic-competitors",
            payload={"competitors": [
                {"competitor_domain": "a.com", "domain_rating": 70, "traffic": 10000, "keywords_common": 100},
                {"competitor_domain": "b.com", "domain_rating": 50, "traffic": 5000, "keywords_common": 50},
            ]},
            context={"target": "example.com", "country": "US"},
        )
        self.assertEqual(result["capability"], "seo.competitor_traffic")
        self.assertIn("2 organic competitor rows", result["evidence"][0]["claim"])

    def test_paid_pages_normalization(self):
        result = normalize_ahrefs_result(
            request_id="req_4",
            endpoint="site-explorer/paid-pages",
            payload={"pages": [
                {"url": "https://a.com/x", "ads_count": 5, "keywords": 20, "sum_traffic": 100},
                {"url": "https://a.com/y", "ads_count": 0, "keywords": 0},
            ]},
            context={"target": "a.com"},
        )
        self.assertEqual(result["capability"], "seo.competitor_ads")
        self.assertIn("1 returned rows show paid-search activity", result["evidence"][0]["claim"])

    def test_refdomains_real_field_name(self):
        result = normalize_ahrefs_result(
            request_id="req_5",
            endpoint="site-explorer/refdomains",
            payload={"refdomains":[
                {"domain":"one.example","domain_rating":50,"links_to_target":3},
                {"domain":"two.example","domain_rating":40,"links_to_target":1},
            ]},
            context={"target":"example.com"},
        )
        self.assertIn("2 distinct referring domains", result["evidence"][0]["claim"])

    def test_unsupported_endpoint_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_ahrefs_result(
                request_id="req_x",
                endpoint="unknown/report",
                payload={},
            )


if __name__ == "__main__":
    unittest.main()
