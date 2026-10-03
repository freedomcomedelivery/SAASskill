import unittest

from saasskill.executors import ExecutionManager


class ExecutionManagerTests(unittest.TestCase):
    def test_dry_run_does_not_need_approval(self):
        state = {"execution_plans": [], "approvals": []}
        manager = ExecutionManager()
        plan = manager.prepare(
            state, provider="google_ads", operation="campaign.create",
            target="customer/123", payload={"name": "test"}, max_spend=100, currency="USD",
        )
        dispatch = manager.dispatch(state, plan_id=plan["id"], apply=False)
        self.assertTrue(dispatch["dry_run"])
        self.assertEqual(plan["status"], "prepared")

    def test_apply_requires_plan_bound_approval(self):
        state = {"execution_plans": [], "approvals": []}
        manager = ExecutionManager()
        plan = manager.prepare(
            state, provider="meta_ads", operation="campaign.create",
            target="act_1", payload={}, max_spend=50, currency="USD",
        )
        state["approvals"].append({
            "id": "a1", "status": "approved", "plan_id": "other",
            "max_spend": 50, "currency": "USD",
        })
        with self.assertRaises(PermissionError):
            manager.dispatch(state, plan_id=plan["id"], approval_id="a1", apply=True)

    def test_spend_cap_is_enforced(self):
        state = {"execution_plans": [], "approvals": []}
        manager = ExecutionManager()
        plan = manager.prepare(
            state, provider="yandex_direct", operation="campaign.update",
            target="1", payload={}, max_spend=200, currency="RUB",
        )
        state["approvals"].append({
            "id": "a1", "status": "approved", "plan_id": plan["id"],
            "max_spend": 100, "currency": "RUB",
        })
        with self.assertRaises(PermissionError):
            manager.dispatch(state, plan_id=plan["id"], approval_id="a1", apply=True)

    def test_exact_approval_dispatches(self):
        state = {"execution_plans": [], "approvals": []}
        manager = ExecutionManager()
        plan = manager.prepare(
            state, provider="apple_ads", operation="campaign.update",
            target="7", payload={"status": "PAUSED"}, max_spend=None, currency="USD",
        )
        state["approvals"].append({
            "id": "a1", "status": "approved", "plan_id": plan["id"],
            "max_spend": None, "currency": "USD",
        })
        dispatch = manager.dispatch(state, plan_id=plan["id"], approval_id="a1", apply=True)
        self.assertFalse(dispatch["dry_run"])
        self.assertEqual(plan["status"], "dispatched")


if __name__ == "__main__":
    unittest.main()
