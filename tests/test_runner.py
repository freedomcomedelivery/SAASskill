import tempfile
import unittest
from pathlib import Path

from saasskill.autopilot import ProjectRunner
from saasskill.state import ProjectStore


class ProjectRunnerTests(unittest.TestCase):
    def test_tick_returns_pending_requests_without_replanning(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "projects")
            state = store.create("X", "x")
            state["stage"] = "market_discovery"
            store.save(state)
            runner = ProjectRunner(store)
            first = runner.tick("x", available_providers=["web", "ahrefs"], auto_advance=False)
            self.assertTrue(first["requests"])
            second = runner.tick("x", available_providers=["web", "ahrefs"], auto_advance=False)
            self.assertEqual(second["status"], "awaiting_provider_results")
            self.assertEqual(
                {x["request_id"] for x in first["requests"]},
                {x["request_id"] for x in second["requests"]},
            )


if __name__ == "__main__":
    unittest.main()
