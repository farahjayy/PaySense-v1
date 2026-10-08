"""Plan status derivation + read-model enrichment (DATABASE.md §3)."""
from datetime import date

from app.db import repo
from app.services.schedule import from_sen, to_sen


def derive_status(installments: list[dict], today: date | None = None) -> str:
    today = today or date.today()
    if installments and all(inst["is_paid"] for inst in installments):
        return "completed"
    if any(not inst["is_paid"] and inst["due_date"] < today for inst in installments):
        return "overdue"
    return "active"


def enrich_plan(plan: dict, installments: list[dict], today: date | None = None) -> dict:
    """Return a new plan dict with computed fields; does not mutate inputs."""
    today = today or date.today()
    ordered = sorted(installments, key=lambda i: i["seq"])
    paid_count = sum(1 for i in ordered if i["is_paid"])
    unpaid = [i for i in ordered if not i["is_paid"]]
    next_due = min((i["due_date"] for i in unpaid), default=None)
    return {
        **plan,
        "status": derive_status(ordered, today),
        "installment_amount": float(ordered[0]["amount"]) if ordered else 0.0,
        # Sum of the real instalments (in sen, so no float drift) — never a re-derived formula.
        "total_payable": from_sen(sum(to_sen(float(i["amount"])) for i in ordered)),
        "paid_count": paid_count,
        "remaining_count": len(ordered) - paid_count,
        "next_due_date": next_due.isoformat() if next_due else None,
    }


def create_plan_with_checkout_payment(plan: dict, schedule: list[dict]) -> dict:
    """Create the plan; what the provider charges at checkout (Atome's first payment, e.g. RM10
    of a RM30 three-payment plan) leaves the balance now. Later instalments leave it when
    marked paid."""
    created = repo.create_plan(plan, schedule)
    prepaid_sen = sum(to_sen(item["amount"]) for item in schedule if item.get("paid_at_checkout"))
    if prepaid_sen:
        repo.adjust_balance(-from_sen(prepaid_sen))
    return created
