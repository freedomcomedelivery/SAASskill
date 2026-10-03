import tempfile
import unittest
from pathlib import Path

from saasskill.host_executor import HostExecutor
from saasskill.providers import ProviderRouter
from saasskill.state import ProjectStore


class ProviderRouterTests(unittest.TestCase):
    def test_semrush_ahrefs_priority_and_override(self):
        router = ProviderRouter(["web", "semrush", "ahrefs"])
        self.assertEqual(router.resolve("seo.keyword_metrics").provider, "semrush")
        self.assertEqual(router.resolve("seo.domain_metrics").provider, "ahrefs")

        router = ProviderRouter(
            ["web", "semrush", "ahrefs"],
            {"seo.keyword_metrics": ["ahrefs", "semrush"]},
        )
        self.assertEqual(router.resolve("seo.keyword_metrics").provider, "ahrefs")

    def test_web_fallback_is_degraded(self):
        route = ProviderRouter(["web"]).resolve("seo.keyword_metrics")
        self.assertEqual(route.provider, "web")
        self.assertEqual(route.effective_capability, "web.search")
        self.assertTrue(route.degraded)

    def test_ads_write_has_no_fake_fallback(self):
        route = ProviderRouter(["web", "ahrefs"]).resolve("ads.campaigns.write")
        self.assertFalse(route.resolved)

    def test_host_plan_routes_market_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "projects")
            state = store.create("X", "x")
            state["stage"] = "market_discovery"
            store.save(state)
            plan = HostExecutor(store).plan("x", available_providers=["web", "ahrefs"])
            routed = {x["work_key"]: x for x in plan["requests"]}
            self.assertEqual(routed["market_players"]["provider"], "web")
            self.assertEqual(routed["market_demand"]["provider"], "ahrefs")
            self.assertEqual(routed["market_structure"]["provider"], "ahrefs")

    def test_apply_result_protects_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "projects")
            store.create("X", "x")
            executor = HostExecutor(store)
            with self.assertRaises(PermissionError):
                executor.apply_result("x", {
                    "request_id": "req_1",
                    "status": "ok",
                    "provider": "web",
                    "capability": "web.search",
                    "state_patch": {"stage": "scale_or_pivot"},
                })

    def test_apply_result_adds_evidence_and_safe_patch(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "projects")
            store.create("X", "x")
            executor = HostExecutor(store)
            out = executor.apply_result("x", {
                "request_id": "req_1",
                "status": "ok",
                "provider": "ahrefs",
                "capability": "seo.keyword_metrics",
                "evidence": [{
                    "kind": "fact",
                    "claim": "Keyword group has measurable demand",
                    "source_ref": "provider://ahrefs/query/1",
                    "confidence": 0.9,
                }],
                "state_patch": {"markets": [{"name": "M", "definition": "D"}]},
            })
            self.assertEqual(out["evidence_count"], 1)
            state = store.load("x")
            self.assertEqual(state["markets"][0]["name"], "M")
            self.assertIn("provider=ahrefs", state["evidence"][0]["notes"])


if __name__ == "__main__":
    unittest.main()
