#!/usr/bin/env python3
"""Small smoke demo for the deterministic runtime."""
import tempfile
from pathlib import Path

from saasskill.orchestrator import Orchestrator
from saasskill.state import ProjectStore

with tempfile.TemporaryDirectory() as tmp:
    store = ProjectStore(Path(tmp) / "projects")
    orch = Orchestrator(store)
    project = store.create("Demo", "demo")
    print(orch.status(project["project_id"]))
    state, gate = orch.advance("demo")
    print({"advanced_to": state["stage"], "gate": gate.status})
