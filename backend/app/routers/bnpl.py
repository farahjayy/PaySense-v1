"""BNPL plans: list/create/detail/delete + instalment mark-paid."""
import logging
from datetime import date

from fastapi import APIRouter, Query

from app.db import repo
from app.errors import bad_request, not_found
from app.schemas import PayInstallmentRequest, PlanCreate, PlanUpdate
from app.services.bills import monthly_bills
from app.services.plan_edit import rename_plan
from app.services.plan_transactions import find_plan_transactions, installment_description, summarize
from app.services.plans import create_plan_with_checkout_payment, derive_status, enrich_plan
from app.services.schedule import build_schedule
from app.services.transaction_ops import delete_payment_transaction

logger = logging.getLogger("paysense")
router = APIRouter(prefix="/api/bnpl", tags=["bnpl"])


def _serialize(plan: dict, include_installments: bool = False) -> dict:
    enriched = enrich_plan(plan, plan["installments"])
    installments = [
        {**inst, "due_date": inst["due_date"].isoformat(), "amount": float(inst["amount"])}
        for inst in enriched["installments"]
    ]
    result = {**enriched, "total_price": float(enriched["total_price"]),
              "interest_rate": float(enriched["interest_rate"])}
    if include_installments:
        result["installments"] = installments
    else:
        result.pop("installments", None)
    return result


def _sync_status(plan: dict) -> None:
    """Persist derived status when it drifted from the stored value."""
    derived = derive_status(plan["installments"])
    if derived != plan["status"]:
        repo.update_plan_status(plan["id"], derived)


@router.get("/plans")
def list_plans(status: str | None = Query(default=None, pattern="^(active|completed|overdue)$")):
    plans = repo.list_plans()
    for plan in plans:
        _sync_status(plan)
    serialized = [_serialize(p) for p in plans]
    if status:
        serialized = [p for p in serialized if p["status"] == status]
    return serialized


@router.post("/plans", status_code=201)
def create_plan(body: PlanCreate):
    schedule = build_schedule(
        body.provider,
        body.total_price,
        body.interest_rate,
        body.num_installments,
        body.purchase_date or date.today(),
        body.first_payment_date,
    )
    plan = create_plan_with_checkout_payment(
        {
            "item_name": body.item_name,
            "provider": body.provider,
            "total_price": body.total_price,
            "interest_rate": body.interest_rate,
            "num_installments": body.num_installments,
            "first_payment_date": schedule[0]["due_date"].isoformat(),
        },
        schedule,
    )
    return _serialize(plan, include_installments=True)


@router.get("/plans/{plan_id}")
def get_plan(plan_id: str):
    plan = repo.get_plan(plan_id)
    if plan is None:
        raise not_found("PLAN_NOT_FOUND", "That BNPL plan doesn't exist.")
    _sync_status(plan)
    return _serialize(plan, include_installments=True)


@router.post("/plans/{plan_id}/installments/{seq}/pay")
def pay_installment(plan_id: str, seq: int, body: PayInstallmentRequest):
    plan = repo.get_plan(plan_id)
    if plan is None:
        raise not_found("PLAN_NOT_FOUND", "That BNPL plan doesn't exist.")
    installment = next((i for i in plan["installments"] if i["seq"] == seq), None)
    if installment is None:
        raise not_found("INSTALLMENT_NOT_FOUND", f"Instalment {seq} doesn't exist on this plan.")
    if installment["is_paid"]:
        raise bad_request("ALREADY_PAID", f"Instalment {seq} is already marked paid.")

    paid_date = body.paid_date or date.today()
    repo.mark_installment_paid(plan_id, seq, paid_date)
    # Paying always takes the money out of the balance, whatever the ledger mode. The logged
    # expense below is inserted plainly (not via the ledger) so it is never subtracted twice.
    repo.adjust_balance(-float(installment["amount"]))

    if body.create_transaction:
        repo.insert_transaction(
            {
                "date": paid_date.isoformat(),
                "amount": float(installment["amount"]),
                "type": "expense",
                "category": "Bills",
                "description": installment_description(plan, seq),
                "is_bnpl": True,
                "bnpl_plan_id": plan_id,
                "source": "manual",
            }
        )

    refreshed = repo.get_plan(plan_id)
    _sync_status(refreshed)
    return _serialize(repo.get_plan(plan_id), include_installments=True)


@router.patch("/plans/{plan_id}")
def update_plan(plan_id: str, body: PlanUpdate):
    """Rename a plan. The item name is the only editable field."""
    plan = repo.get_plan(plan_id)
    if plan is None:
        raise not_found("PLAN_NOT_FOUND", "That BNPL plan doesn't exist.")
    rename_plan(plan, body.item_name)
    return _serialize(repo.get_plan(plan_id), include_installments=True)


@router.get("/bills")
def bills():
    """Instalments due across every tracked plan, grouped by calendar month."""
    return monthly_bills(repo.list_plans())


@router.get("/plans/{plan_id}/transactions")
def plan_transactions(plan_id: str):
    """Preview: the expense transactions this plan's paid instalments logged."""
    plan = repo.get_plan(plan_id)
    if plan is None:
        raise not_found("PLAN_NOT_FOUND", "That BNPL plan doesn't exist.")
    return summarize(find_plan_transactions(plan))


@router.delete("/plans/{plan_id}")
def delete_plan(plan_id: str, delete_transactions: bool = Query(default=False)):
    """Delete a plan. Its logged transactions are KEPT unless delete_transactions=true."""
    plan = repo.get_plan(plan_id)
    if plan is None:
        raise not_found("PLAN_NOT_FOUND", "That BNPL plan doesn't exist.")
    matches = find_plan_transactions(plan) if delete_transactions else []
    repo.delete_plan(plan_id)

    deleted, failed = 0, 0
    for transaction in matches:
        try:
            if delete_payment_transaction(transaction):
                deleted += 1
        except Exception:
            failed += 1
            logger.exception("Couldn't delete transaction %s while deleting plan %s", transaction["id"], plan_id)
    return {"deleted_transactions": deleted, "failed_transactions": failed}
