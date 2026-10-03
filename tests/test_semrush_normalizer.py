import unittest

from saasskill.semrush import normalize_semrush_result


class SemrushNormalizerTests(unittest.TestCase):
    def test_keyword_csv(self):
        payload = "Keyword;Search Volume;CPC;Competition;Keyword Difficulty Index\nai seo tool;880;6.63;0.3;44\nseo software;590;9.50;0.4;55\n"
        result = normalize_semrush_result(
            request_id="r1",
            report_type="phrase_these",
            payload=payload,
            context={"query": "seo tools"},
        )
        self.assertEqual(result["provider"], "semrush")
        self.assertEqual(result["capability"], "seo.keyword_metrics")
        self.assertIn("1,470", result["evidence"][0]["claim"])

    def test_competitor_csv(self):
        payload = "Domain;Common Keywords;Organic Keywords;Organic Traffic;Adwords Keywords\na.com;100;2000;5000;10\nb.com;80;1500;4000;5\n"
        result = normalize_semrush_result(
            request_id="r2",
            report_type="domain_organic_organic",
            payload=payload,
            context={"target": "example.com"},
        )
        self.assertEqual(result["capability"], "seo.competitor_traffic")
        self.assertIn("2 domain/competitor rows", result["evidence"][0]["claim"])

    def test_unsupported_report(self):
        with self.assertRaises(ValueError):
            normalize_semrush_result(request_id="r3", report_type="nope", payload=[])


if __name__ == "__main__":
    unittest.main()
