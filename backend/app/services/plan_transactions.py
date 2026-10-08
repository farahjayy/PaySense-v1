"""The expense transactions a plan's paid instalments logged.

Marking an instalment paid logs one expense linked to the plan by transactions.bnpl_plan_id
(migration 002), so the plan's transactions are simply the rows carrying its id. Text is never
used to decide what belongs to a plan. Rows logged before the link existed have a null
bnpl_plan_id until scripts/backfill_bnpl_plan_id.py links them; until then they are neither
offered nor deleted (a look-alike description is not proof).
"""
from app.db import repo
from app.services.schedule import from_sen, to_sen


def installment_description(plan: dict, seq: int) -> str:
    return f"{plan['provider']} instalment {seq}/{plan['num_installments']} \u2014 {plan['item_name']}"


def find_plan_transactions(plan: dict) -> list[dict]:
    return repo.list_transactions_for_plan(plan["id"])


def summarize(transactions: list[dict]) -> dict:
    return {
        "count": len(transactions),
        "total": from_sen(sum(to_sen(float(t["amount"])) for t in transactions)),
        "items": [
            {"id": t["id"], "date": str(t["date"])[:10], "amount": float(t["amount"]), "description": t["description"]}
            for t in transactions
        ],
    }
