import unittest

from saasskill.camoufox_parser import extract_html_snapshot, validate_public_url


class CamoufoxParserTests(unittest.TestCase):
    def test_extracts_commercial_surface(self):
        html = """
        <html><head><title>Acme</title><meta name="description" content="Save time"></head>
        <body><h1>Reports in 5 minutes</h1><a href="/pricing">Pricing $29</a>
        <button>Start free trial</button><form><input name="email" type="email"></form>
        <script type="application/ld+json">{"@type":"SoftwareApplication","name":"Acme"}</script>
        </body></html>
        """
        snap = extract_html_snapshot(html, url="https://example.com")
        self.assertEqual(snap["title"], "Acme")
        self.assertIn("Start free trial", snap["ctas"])
        self.assertIn("$29", snap["prices"])
        self.assertEqual(snap["forms"], 1)
        self.assertEqual(snap["json_ld"][0]["name"], "Acme")

    def test_nested_anchor_text_is_preserved(self):
        snap = extract_html_snapshot('<a href="/signup"><span>Start</span> <strong>free trial</strong></a>')
        self.assertEqual(snap["links"][0]["text"], "Start free trial")
        self.assertIn("Start free trial", snap["ctas"])

    def test_challenge_is_reported_not_solved(self):
        snap = extract_html_snapshot("<html><body>Verify you are human CAPTCHA</body></html>")
        self.assertTrue(snap["challenge_detected"])

    def test_private_ip_is_rejected(self):
        with self.assertRaises(PermissionError):
            validate_public_url("http://127.0.0.1/admin")

    def test_domain_allowlist_is_enforced_before_fetch(self):
        with self.assertRaises(PermissionError):
            validate_public_url("https://example.com", {"allowed.example"})

    def test_non_http_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_public_url("file:///etc/passwd")


if __name__ == "__main__":
    unittest.main()
