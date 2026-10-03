import unittest

from saasskill.parser_normalizer import normalize_public_page_result


class ParserNormalizerTests(unittest.TestCase):
    def test_audit_snapshot_merge_patch(self):
        result = normalize_public_page_result(
            request_id="r1",
            snapshot={
                "url": "https://example.com",
                "title": "Acme",
                "meta_description": "Fast reports",
                "headings": [{"level": "h1", "text": "Fast reports"}],
                "ctas": ["Start free"],
                "prices": ["$29"],
                "forms": 1,
                "inputs": [{"name": "email"}],
                "challenge_detected": False,
            },
            context={"workflow": "existing_project_audit"},
        )
        self.assertEqual(result["capability"], "web.browser_parse")
        landing = result["state_merge_patch"]["audit_snapshot"]["landing"]
        self.assertEqual(landing["cta_count"], 1)
        self.assertEqual(landing["prices"], ["$29"])


if __name__ == "__main__":
    unittest.main()
