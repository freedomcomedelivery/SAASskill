import tempfile
import unittest
from pathlib import Path

from saasskill.adapters import MockActionAdapter
from saasskill.gates import evaluate_stage
from saasskill.orchestrator import Orchestrator
from saasskill.state import ProjectStore, add_evidence


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.orch = Orchestrator(self.store)

    def tearDown(self):
        self.tmp.cleanup()

    def test_auto_project_id_slug(self):
        state = self.store.create("Podcast Shorts")
        self.assertTrue(state["project_id"].startswith("podcast-shorts-"))

    def test_init_and_intake_advance(self):
        state = self.store.create("Podcast Shorts", "podcast-shorts")
        self.assertEqual(state["stage"], "intake")
        self.assertTrue(evaluate_stage(state).passed)
        state, gate = self.orch.advance("podcast-shorts")
        self.assertTrue(gate.passed)
        self.assertEqual(state["stage"], "personal_concept")

    def test_market_requires_evidence(self):
        state = self.store.create("X", "x")
        state["stage"] = "market_discovery"
        state["markets"] = [{"name": "AI editing", "definition": "Tools"}]
        self.store.save(state)
        gate = evaluate_stage(self.store.load("x"))
        self.assertEqual(gate.status, "needs_evidence")

        state = self.store.load("x")
        state["markets"][0].update({
            "players": ["a", "b", "c"],
            "green_signals": {"many_small_players": True, "many_transactions": True, "easy_switching": True},
            "evidence_ids": ["ev_1"],
        })
        self.store.save(state)
        self.assertTrue(evaluate_stage(self.store.load("x")).passed)

    def test_idea_gate_requires_close_refs_and_price(self):
        state = self.store.create("X", "x")
        state["stage"] = "idea_selection"
        state["selected_idea_id"] = "i1"
        state["ideas"] = [{
            "id": "i1",
            "one_liner": "AI clips",
            "primary_pain": "Editing takes too long",
            "references": ["a", "b"],
            "avg_competitor_check": None,
            "usage_frequency": "weekly",
            "feasible_as_pet_project": True,
            "personal_fit": True,
            "decision": "selected",
        }]
        gate = evaluate_stage(state)
        self.assertEqual(gate.status, "needs_evidence")
        self.assertIn("3–5 close references", gate.missing)

        state["ideas"][0]["references"].append("c")
        state["ideas"][0]["avg_competitor_check"] = 39
        self.assertTrue(evaluate_stage(state).passed)

    def test_force_transition_requires_reason(self):
        state = self.store.create("X", "x")
        state["stage"] = "market_discovery"
        self.store.save(state)
        with self.assertRaises(ValueError):
            self.orch.advance("x", force=True)
        state, _ = self.orch.advance("x", force=True, reason="manual methodology override")
        self.assertEqual(state["stage"], "idea_generation")
        self.assertTrue(state["stage_history"][-1]["forced"])

    def test_evidence_and_action_approval(self):
        state = self.store.create("X", "x")
        ev = add_evidence(state, kind="fact", claim="Three competitors found", source_ref="https://example.com")
        self.assertTrue(ev["id"].startswith("ev_"))
        self.store.save(state)

        adapter = MockActionAdapter()
        with self.assertRaises(PermissionError):
            adapter.execute({"type": "launch"}, approval={"status": "pending"})
        result = adapter.execute({"type": "launch"}, approval={"id": "a1", "status": "approved"})
        self.assertEqual(result["status"], "executed")

    def test_work_queue_routes_market_research(self):
        from saasskill.workplan import build_work_queue
        state = self.store.create("X", "x")
        state["stage"] = "market_discovery"
        queue = build_work_queue(state)
        keys = {x["key"] for x in queue}
        self.assertIn("market_players", keys)
        self.assertIn("market_demand", keys)

    def test_work_queue_requires_approval_before_launch_action(self):
        from saasskill.workplan import build_work_queue
        state = self.store.create("X", "x")
        state["stage"] = "launch"
        queue = build_work_queue(state)
        self.assertEqual(queue[0]["kind"], "approval")
        state["approvals"] = [{"id": "a1", "status": "approved"}]
        queue = build_work_queue(state)
        self.assertEqual(queue[0]["kind"], "action")
        self.assertEqual(queue[0]["key"], "prepare_execution_plan")


if __name__ == "__main__":
    unittest.main()
