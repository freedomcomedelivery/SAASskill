import tempfile
import unittest
from pathlib import Path

from saasskill.audit import commercial_readiness, derive_audit_findings, growth_priorities, refresh_audit_report
from saasskill.autopilot import ProjectRunner
from saasskill.gates import evaluate_stage
from saasskill.orchestrator import Orchestrator
from saasskill.state import ProjectStore


class ExistingProjectAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")

    def tearDown(self):
        self.tmp.cleanup()

    def test_audit_workflow_starts_at_audit_intake(self):
        state = self.store.create("Existing SaaS", "existing", "existing_project_audit")
        self.assertEqual(state["workflow"], "existing_project_audit")
        self.assertEqual(state["stage"], "audit_intake")
        self.assertTrue(evaluate_stage(state).passed)

    def test_orchestrator_uses_audit_stage_machine(self):
        self.store.create("Existing SaaS", "existing", "existing_project_audit")
        state, gate = Orchestrator(self.store).advance("existing")
        self.assertTrue(gate.passed)
        self.assertEqual(state["stage"], "audit_snapshot")

    def test_audit_detects_core_methodology_errors(self):
        state = self.store.create("Existing SaaS", "existing", "existing_project_audit")
        state["audit_snapshot"] = {
            "product_status": "live",
            "geo": "US",
            "avatars": ["freelancers", "agencies"],
            "pains": ["too much work", "low revenue"],
            "benefits": ["save time", "make money"],
            "channels": [{"name": "meta"}, {"name": "outreach"}],
            "primary_channel": "meta",
            "product_is_searched": True,
            "controlled_funnel": False,
            "funnel": {"reach": 500, "clicks": 20, "leads": 2, "qualified_leads": None, "payments": 0},
            "analytics": {"configured": False},
            "sales_process": {},
            "offer": {},
        }
        codes = {x["code"] for x in derive_audit_findings(state)}
        self.assertIn("all_for_everyone", codes)
        self.assertIn("wrong_channel", codes)
        self.assertIn("funnel_of_fate", codes)
        self.assertIn("no_decomposition_debugging", codes)
        self.assertIn("sales_process_gap", codes)
        self.assertIn("offer_gap", codes)

    def test_readiness_progression(self):
        state = self.store.create("Existing SaaS", "existing", "existing_project_audit")
        state["audit_snapshot"] = {
            "avatars": "agencies",
            "pains": "manual reporting",
            "benefits": "save analyst hours",
            "controlled_funnel": True,
            "funnel_definition": {"steps": ["reach", "clicks", "leads", "qualified_leads", "payments"]},
            "funnel": {"reach": 5000, "clicks": 400, "leads": 40, "qualified_leads": 15, "payments": 0},
            "analytics": {"configured": True},
            "sales_process": {
                "qualification": "defined",
                "need_discovery": "defined",
                "demo_or_value_delivery": "defined",
                "close_or_payment_ask": "defined",
            },
            "offer": {"primary_cta": "book demo", "primary_benefit": "save analyst hours"},
            "economics": {"target_cac": 200, "ltv_estimate": 1200},
        }
        self.assertEqual(commercial_readiness(state), "ready_for_controlled_sales")
        state["audit_snapshot"]["funnel"]["payments"] = 3
        self.assertEqual(commercial_readiness(state), "sales_validated")
        state["economics"] = {"target_cac": 200, "ltv_estimate": 1200, "viability": "pass"}
        state["iterations"] = [{"id": "i1", "actual": {"payments": 3}, "conclusion": "continue"}]
        self.assertEqual(commercial_readiness(state), "ready_to_scale")

    def test_resolved_findings_do_not_block_forever(self):
        state = self.store.create("Existing SaaS", "existing", "existing_project_audit")
        state["audit_snapshot"] = {
            "avatars": ["a", "b"], "pains": "p", "benefits": "b",
            "controlled_funnel": False, "funnel": {},
            "analytics": {"configured": False}, "sales_process": {}, "offer": {},
        }
        report = refresh_audit_report(state)
        self.assertEqual(report["commercial_readiness"], "not_ready")
        state["audit_snapshot"].update({
            "avatars": "a",
            "controlled_funnel": True,
            "funnel_definition": {"steps": ["reach", "clicks", "leads", "qualified_leads", "payments"]},
            "funnel": {"reach": 1000, "clicks": 100, "leads": 20, "qualified_leads": 10, "payments": 0},
            "analytics": {"configured": True},
            "sales_process": {
                "qualification": "yes", "need_discovery": "yes",
                "demo_or_value_delivery": "yes", "close_or_payment_ask": "yes",
            },
            "offer": {"primary_cta": "buy", "primary_benefit": "b"},
            "economics": {"target_cac": 10, "ltv_estimate": 100},
        })
        report = refresh_audit_report(state)
        resolved_codes = {x["code"] for x in report["findings"] if x["status"] == "resolved"}
        self.assertIn("all_for_everyone", resolved_codes)
        self.assertIn("funnel_of_fate", resolved_codes)
        self.assertEqual(report["commercial_readiness"], "ready_for_controlled_sales")

    def test_growth_plan_moves_to_controlled_sales_when_repairs_done(self):
        from saasskill.audit import build_growth_plan
        state = self.store.create("Existing SaaS", "existing", "existing_project_audit")
        state["audit_snapshot"] = {
            "product_status": "live", "avatars": "a", "pains": "p", "benefits": "b",
            "primary_channel": "search", "product_is_searched": True,
            "controlled_funnel": True,
            "funnel_definition": {"steps": ["reach", "clicks", "leads", "qualified_leads", "payments"]},
            "funnel": {"reach": 1000, "clicks": 100, "leads": 20, "qualified_leads": 10, "payments": 0},
            "analytics": {"configured": True},
            "sales_process": {
                "qualification": "yes", "need_discovery": "yes",
                "demo_or_value_delivery": "yes", "close_or_payment_ask": "yes",
            },
            "offer": {"primary_cta": "buy", "primary_benefit": "b"},
            "economics": {"target_cac": 10, "ltv_estimate": 100},
        }
        plan = build_growth_plan(state)
        self.assertEqual(plan["readiness"], "ready_for_controlled_sales")
        self.assertEqual(plan["actions"][0]["id"], "action_controlled_sales_test")
        self.assertTrue(plan["actions"][0]["side_effect"])
        self.assertEqual(plan["actions"][0]["capability"], "ads.campaigns.write")

    def test_growth_priorities_put_blockers_first(self):
        state = self.store.create("Existing SaaS", "existing", "existing_project_audit")
        state["audit_snapshot"] = {
            "product_status": "live",
            "avatars": ["a", "b"],
            "pains": "p",
            "benefits": "b",
            "controlled_funnel": False,
            "funnel": {},
            "analytics": {"configured": False},
            "sales_process": {},
            "offer": {},
        }
        priorities = growth_priorities(state)
        self.assertTrue(priorities)
        self.assertEqual(priorities[0]["severity"], "blocking")

    def test_tick_advances_audit_intake_and_plans_snapshot(self):
        self.store.create("Existing SaaS", "existing", "existing_project_audit")
        tick = ProjectRunner(self.store).tick("existing", available_providers=["web"], auto_advance=True)
        self.assertEqual(tick["advanced"]["to"], "audit_snapshot")
        self.assertEqual(tick["stage"], "audit_snapshot")


if __name__ == "__main__":
    unittest.main()
