import unittest
from unittest.mock import patch

from saasskill.camofox_rest import fetch_snapshot


class CamofoxRestTests(unittest.TestCase):
    def test_public_snapshot_lifecycle(self):
        calls=[]
        def fake(path, method="GET", body=None, timeout=30.0):
            calls.append((path,method,body))
            if path == "/tabs":
                return {"tabId":"t1","url":"https://example.com","title":"Example"}
            if "/snapshot?" in path:
                return {"url":"https://example.com","snapshot":"[heading] Example\n[link e1] Pricing"}
            if method == "DELETE":
                return {}
            raise AssertionError(path)
        with patch("saasskill.camofox_rest._call", side_effect=fake):
            out=fetch_snapshot("https://example.com",allowed_domains={"example.com"})
        self.assertEqual(out["provider"],"camofox-browser-rest")
        self.assertIn("[heading]",out["snapshot"])
        self.assertTrue(any(method=="DELETE" for _,method,_ in calls))

    def test_private_url_is_rejected(self):
        with self.assertRaises(PermissionError):
            fetch_snapshot("http://127.0.0.1:8080")


if __name__ == "__main__":
    unittest.main()
