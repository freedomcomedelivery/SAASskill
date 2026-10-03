from __future__ import annotations

from typing import Any


def _rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [dict(x) for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in ("data", "results", "rows", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [dict(x) for x in value if isinstance(x, dict)]
        return [payload]
    return []


def _stripe_success(row: dict[str, Any]) -> bool:
    object_type = row.get("object")
    status = str(row.get("status") or "").lower()
    if object_type == "payment_intent":
        return status == "succeeded"
    if object_type == "invoice":
        return bool(row.get("paid")) or status == "paid"
    if object_type == "charge":
        return bool(row.get("paid")) and not bool(row.get("refunded"))
    return status in {"succeeded", "paid"} or row.get("paid") is True


def _stripe_amount_major(row: dict[str, Any]) -> float:
    amount = row.get("amount_received")
    if amount is None:
        amount = row.get("amount_paid")
    if amount is None:
        amount = row.get("amount")
    try:
        return float(amount or 0) / 100.0
    except (TypeError, ValueError):
        return 0.0


def normalize_payments_result(*, provider: str, request_id: str, payload: Any, context: dict[str, Any] | None = None) -> dict[str, Any]:
    if provider not in {"stripe", "payments"}:
        raise ValueError(f"Unsupported payments provider: {provider}")
    context = dict(context or {})
    rows = _rows(payload)
    successes = []
    revenue = 0.0
    currencies = set()

    for row in rows:
        if provider == "stripe":
            success = _stripe_success(row)
            amount = _stripe_amount_major(row)
        else:
            success = bool(row.get("paid") or row.get("status") in {"paid", "succeeded"})
            try:
                amount = float(row.get("amount") or row.get("revenue") or 0)
            except (TypeError, ValueError):
                amount = 0.0
        if not success:
            continue
        successes.append(row)
        revenue += amount
        if row.get("currency"):
            currencies.add(str(row["currency"]).upper())

    count = len(successes)
    currency_note = ",".join(sorted(currencies)) if currencies else context.get("currency")
    merge_patch = {}
    if context.get("workflow") == "existing_project_audit":
        merge_patch = {
            "audit_snapshot": {
                "verified_payments": {
                    "provider": provider,
                    "count": count,
                    "revenue": round(revenue, 2),
                    "currency": currency_note,
                }
            }
        }

    return {
        "request_id": request_id,
        "provider": provider,
        "capability": "payments.transactions.read",
        "degraded": False,
        "status": "ok",
        "data": {"rows": rows, "successful": successes, "count": count, "revenue": round(revenue, 2), "currency": currency_note},
        "evidence": [{
            "kind": "fact",
            "claim": f"{provider} returned {count} verified successful payment records with normalized revenue {revenue:.2f}" + (f" {currency_note}" if currency_note else "") + ".",
            "source_ref": context.get("source_ref") or f"provider://{provider}/payments",
            "source_title": f"{provider} verified payments",
            "confidence": 0.995,
            "notes": "Payment evidence is kept separate from ad-platform conversions and CRM lifecycle labels.",
        }],
        "state_patch": {},
        "state_merge_patch": merge_patch,
    }
