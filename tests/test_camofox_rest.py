import unittest
from unittest.mock import patch

from saasskill.camofox_rest import fetch_snapshot


class CamofoxRestTests(unittest.TestCase):
    def test_real_camofox_yaml_snapshot_format(self):
        from saasskill.camofox_rest import accessibility_to_surface
        surface=accessibility_to_surface({
            "url":"https://example.com",
            "title":"Example",
            "snapshot":'- heading "Hello World"\n- link "Pricing $29" [e1]\n- button "Get started" [e2]\n',
        })
        self.assertEqual(surface["headings"][0]["text"],"Hello World")
        self.assertEqual(surface["links"][0]["ref"],"e1")
        self.assertIn("Get started",surface["ctas"])
        self.assertIn("$29",surface["prices"])

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

    def test_open_extract_close_lifecycle(self):
        from saasskill.camofox_rest import open_snapshot, extract_refs, close_snapshot
        calls=[]
        def fake(path, method="GET", body=None, timeout=30.0):
            calls.append((path,method,body))
            if path == "/tabs":
                return {"tabId":"t1","url":"https://example.com","title":"Example"}
            if "/snapshot?" in path:
                return {"url":"https://example.com","snapshot":'- link "Pricing" [e1]'}
            if path.endswith("/extract"):
                return {"ok":True,"data":{"price":"Pricing"}}
            if method=="DELETE":
                return {"ok":True}
            raise AssertionError(path)
        with patch("saasskill.camofox_rest._call", side_effect=fake):
            handle=open_snapshot("https://example.com",allowed_domains={"example.com"})
            out=extract_refs("t1",user_id=handle["user_id"],schema={"type":"object","properties":{"price":{"type":"string","x-ref":"e1"}}})
            close_snapshot("t1",user_id=handle["user_id"])
        self.assertEqual(out["data"]["price"],"Pricing")
        self.assertTrue(any(method=="DELETE" for _,method,_ in calls))

    def test_private_url_is_rejected(self):
        with self.assertRaises(PermissionError):
            fetch_snapshot("http://127.0.0.1:8080")


if __name__ == "__main__":
    unittest.main()
