from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class ResearchAdapter(Protocol):
    def search(self, query: str, *, limit: int = 10) -> list[dict[str, Any]]:
        """Return source-backed observations; caller converts them to evidence."""


class MetricsAdapter(Protocol):
    def funnel_snapshot(self, channel_plan: dict[str, Any]) -> dict[str, Any]:
        """Read observed funnel metrics; never invent unavailable metrics."""


class ActionAdapter(Protocol):
    def prepare(self, action: dict[str, Any]) -> dict[str, Any]:
        """Prepare an external side effect without executing it."""

    def execute(self, action: dict[str, Any], *, approval: dict[str, Any]) -> dict[str, Any]:
        """Execute only when explicit approval is present and valid."""


@dataclass
class AdapterRegistry:
    research: ResearchAdapter | None = None
    metrics: MetricsAdapter | None = None
    action: ActionAdapter | None = None


class MockResearchAdapter:
    def __init__(self, results: list[dict[str, Any]] | None = None) -> None:
        self.results = results or []

    def search(self, query: str, *, limit: int = 10) -> list[dict[str, Any]]:
        return self.results[:limit]


class MockMetricsAdapter:
    def __init__(self, snapshot: dict[str, Any] | None = None) -> None:
        self.snapshot = snapshot or {}

    def funnel_snapshot(self, channel_plan: dict[str, Any]) -> dict[str, Any]:
        return dict(self.snapshot)


class MockActionAdapter:
    def prepare(self, action: dict[str, Any]) -> dict[str, Any]:
        return {"status": "prepared", "action": action}

    def execute(self, action: dict[str, Any], *, approval: dict[str, Any]) -> dict[str, Any]:
        if approval.get("status") != "approved":
            raise PermissionError("Explicit approved approval is required")
        return {"status": "executed", "action": action, "approval_id": approval.get("id")}
