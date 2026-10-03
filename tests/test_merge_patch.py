import tempfile
import unittest
from pathlib import Path

from saasskill.host_executor import HostExecutor
from saasskill.state import ProjectStore


class MergePatchTests(unittest.TestCase):
    def test_merge_patch_preserves_existing_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "projects")
            state = store.create("Audit", "audit", "existing_project_audit")
            state["stage"] = "audit_snapshot"
            state["audit_snapshot"] = {"geo": "US", "product_status": "live"}
            state["pending_tool_requests"] = [{
                "request_id": "r1",
                "status": "pending",
                "work_key": "product_surface",
                "provider": "camoufox",
                "effective_capability": "web.browser_parse",
                "side_effect": False,
                "degraded": False,
            }]
            store.save(state)
            HostExecutor(store).apply_result("audit", {
                "request_id": "r1",
                "status": "ok",
                "provider": "camoufox",
                "capability": "web.browser_parse",
                "state_merge_patch": {
                    "audit_snapshot": {"landing": {"title": "Acme"}},
                },
            })
            saved = store.load("audit")["audit_snapshot"]
            self.assertEqual(saved["geo"], "US")
            self.assertEqual(saved["landing"]["title"], "Acme")


if __name__ == "__main__":
    unittest.main()
