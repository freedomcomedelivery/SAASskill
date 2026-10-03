from __future__ import annotations

import argparse
import json
import uuid
from typing import Any

from .gates import evaluate_stage
from .orchestrator import Orchestrator
from .state import ProjectStore, add_evidence, dotted_set, utc_now


def _jsonish(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _dump(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="saasskill", description="Pet Project Launch Operator runtime")
    p.add_argument("--root", default=".saasskill/projects", help="Project state directory")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("init", help="Create project state")
    s.add_argument("name")
    s.add_argument("--project-id")

    sub.add_parser("list", help="List local projects")

    for name in ["status", "show", "gate", "plan"]:
        s = sub.add_parser(name)
        s.add_argument("project_id")

    s = sub.add_parser("route", help="Route the current work plan to available providers")
    s.add_argument("project_id")
    s.add_argument("--provider", action="append", default=[], help="Available logical provider: web, semrush, ahrefs, ads, analytics, crm")

    s = sub.add_parser("advance")
    s.add_argument("project_id")
    s.add_argument("--force", action="store_true")
    s.add_argument("--reason")

    s = sub.add_parser("set")
    s.add_argument("project_id")
    s.add_argument("field", help="Dotted state path")
    s.add_argument("value", help="JSON value; plain strings are accepted")

    s = sub.add_parser("add-evidence")
    s.add_argument("project_id")
    s.add_argument("--kind", required=True, choices=["fact", "estimate", "hypothesis", "course_heuristic", "user_constraint"])
    s.add_argument("--claim", required=True)
    s.add_argument("--source-ref")
    s.add_argument("--source-title")
    s.add_argument("--confidence", type=float, default=0.8)
    s.add_argument("--supports", action="append", default=[])
    s.add_argument("--formula")
    s.add_argument("--assumption", action="append", default=[])
    s.add_argument("--notes")

    s = sub.add_parser("approval")
    s.add_argument("project_id")
    s.add_argument("action", choices=["create", "approve", "reject"])
    s.add_argument("--id")
    s.add_argument("--action-type")
    s.add_argument("--target")
    s.add_argument("--summary")
    s.add_argument("--max-spend", type=float)
    s.add_argument("--currency")
    s.add_argument("--duration")
    s.add_argument("--rollback")

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = ProjectStore(args.root)
    orch = Orchestrator(store)

    if args.command == "init":
        _dump(store.create(args.name, args.project_id))
        return 0
    if args.command == "list":
        _dump(store.list_projects())
        return 0
    if args.command == "status":
        _dump(orch.status(args.project_id))
        return 0
    if args.command == "show":
        _dump(store.load(args.project_id))
        return 0
    if args.command == "gate":
        _dump(evaluate_stage(store.load(args.project_id)).to_dict())
        return 0
    if args.command == "plan":
        from .workplan import build_work_queue
        _dump(build_work_queue(store.load(args.project_id)))
        return 0
    if args.command == "route":
        from .host_executor import HostExecutor
        _dump(HostExecutor(store).plan(args.project_id, available_providers=args.provider))
        return 0
    if args.command == "advance":
        state, gate = orch.advance(args.project_id, force=args.force, reason=args.reason)
        _dump({"stage": state["stage"], "gate": gate.to_dict(), "next_action": state.get("next_action")})
        return 0 if gate.passed or args.force else 2
    if args.command == "set":
        state = store.load(args.project_id)
        dotted_set(state, args.field, _jsonish(args.value))
        gate = evaluate_stage(state)
        state["blockers"] = gate.missing or gate.reasons
        state["next_action"] = gate.next_action
        state.setdefault("action_log", []).append({"type": "state_set", "field": args.field, "at": utc_now()})
        store.save(state)
        _dump({"ok": True, "field": args.field, "gate": gate.to_dict()})
        return 0
    if args.command == "add-evidence":
        state = store.load(args.project_id)
        item = add_evidence(
            state,
            kind=args.kind,
            claim=args.claim,
            source_ref=args.source_ref,
            source_title=args.source_title,
            confidence=args.confidence,
            supports=args.supports,
            formula=args.formula,
            assumptions=args.assumption,
            notes=args.notes,
        )
        store.save(state)
        _dump(item)
        return 0
    if args.command == "approval":
        state = store.load(args.project_id)
        approvals = state.setdefault("approvals", [])
        if args.action == "create":
            if not all([args.action_type, args.target, args.summary]):
                raise SystemExit("approval create requires --action-type, --target and --summary")
            item = {
                "id": args.id or f"apr_{uuid.uuid4().hex[:10]}",
                "action_type": args.action_type,
                "target": args.target,
                "summary": args.summary,
                "max_spend": args.max_spend,
                "currency": args.currency,
                "duration": args.duration,
                "rollback_or_pause": args.rollback,
                "status": "pending",
                "created_at": utc_now(),
            }
            approvals.append(item)
            store.save(state)
            _dump(item)
            return 0
        if not args.id:
            raise SystemExit("approval approve/reject requires --id")
        item = next((x for x in approvals if x.get("id") == args.id), None)
        if item is None:
            raise SystemExit(f"approval not found: {args.id}")
        item["status"] = "approved" if args.action == "approve" else "rejected"
        item["decided_at"] = utc_now()
        store.save(state)
        _dump(item)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
