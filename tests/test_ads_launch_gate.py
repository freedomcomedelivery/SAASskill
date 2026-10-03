import tempfile
import unittest
from pathlib import Path

from saasskill.executors import ExecutionManager
from saasskill.gates import evaluate_stage
from saasskill.state import ProjectStore


class AdsLaunchGateTests(unittest.TestCase):
    def test_ads_launch_requires_executed_plan_not_merely_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "projects")
            state = store.create("X", "x")
            state["stage"] = "launch"
            state["channel_plan"] = {"channel": "search"}
            manager = ExecutionManager()
            plan = manager.prepare(
                state, provider="google_ads", operation="campaign.create",
                target="123", payload={"name": "Test"}, max_spend=100, currency="USD",
            )
            state["approvals"] = [{
                "id": "a1", "status": "approved", "plan_id": plan["id"],
                "max_spend": 100, "currency": "USD",
            }]
            self.assertFalse(evaluate_stage(state).passed)
            manager.dispatch(state, plan_id=plan["id"], approval_id="a1", apply=True)
            self.assertFalse(evaluate_stage(state).passed)
            manager.complete(state, plan_id=plan["id"], result={"status": "ok"})
            self.assertTrue(evaluate_stage(state).passed)


if __name__ == "__main__":
    unittest.main()
