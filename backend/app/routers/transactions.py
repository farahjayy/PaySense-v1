"""Transactions CRUD + monthly summary."""
import logging

from fastapi import APIRouter, Query

from app.db import repo
from app.errors import not_found
from app.schemas import TransactionCreate, TransactionUpdate
from app.services import ledger
from app.services.transaction_ops import delete_with_ledger, is_ledger_mode

logger = logging.getLogger("paysense")
router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("")
def list_transactions(
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    category: str | None = None,
    type: str | None = Query(default=None, pattern="^(income|expense|savings)$"),
    search: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    items, total = repo.list_transactions(
        month=month, category=category, type_=type, search=search, limit=limit, offset=offset
    )
    return {"items": items, "total": total}


@router.get("/summary")
def month_summary(month: str = Query(pattern=r"^\d{4}-\d{2}$")):
    rows = repo.month_transactions(month)
    income = sum(float(r["amount"]) for r in rows if r["type"] == "income")
    expenses = sum(float(r["amount"]) for r in rows if r["type"] == "expense")

    by_category: dict[str, float] = {}
    for r in rows:
        if r["type"] == "expense":
            by_category[r["category"]] = by_category.get(r["category"], 0.0) + float(r["amount"])
    breakdown = [
        {
            "category": category,
            "total": round(total, 2),
            "pct": round(total / expenses * 100, 1) if expenses > 0 else 0.0,
        }
        for category, total in sorted(by_category.items(), key=lambda kv: kv[1], reverse=True)
    ]
    return {"income": round(income, 2), "expenses": round(expenses, 2), "by_category": breakdown}


@router.post("", status_code=201)
def create_transaction(body: TransactionCreate):
    payload = body.model_dump()
    payload["date"] = payload["date"].isoformat()
    created = repo.insert_transaction(payload)
    if is_ledger_mode():
        repo.adjust_balance(ledger.transaction_delta(created))
    return created


@router.put("/{transaction_id}")
def update_transaction(transaction_id: str, body: TransactionUpdate):
    payload = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
    if "date" in payload and payload["date"] is not None:
        payload["date"] = payload["date"].isoformat()

    apply_ledger = is_ledger_mode()
    before = repo.get_transaction(transaction_id) if apply_ledger else None

    updated = repo.update_transaction(transaction_id, payload)
    if updated is None:
        raise not_found("TRANSACTION_NOT_FOUND", "That transaction doesn't exist (it may have been deleted).")

    if apply_ledger and before is not None:
        new_type = payload.get("type", before["type"])
        new_amount = payload.get("amount", before["amount"])
        delta = ledger.edit_delta(before, new_type, new_amount)
        if delta != 0:
            repo.adjust_balance(delta)
    return updated


@router.delete("/{transaction_id}", status_code=204)
def delete_transaction(transaction_id: str):
    if not delete_with_ledger(transaction_id):
        raise not_found("TRANSACTION_NOT_FOUND", "That transaction doesn't exist (it may have been deleted).")
