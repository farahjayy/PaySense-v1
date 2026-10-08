"""Data access layer — all Supabase reads/writes live here.

Dates come back from PostgREST as ISO strings; helpers convert to date objects
before anything reaches the service layer.
"""
from datetime import date, datetime, timezone

from app.db.client import get_db


def _parse_date(value) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


# --- app_state ---

def get_app_state() -> dict:
    result = get_db().table("app_state").select("*").eq("id", 1).single().execute()
    return result.data


def update_balance(current_balance: float) -> dict:
    result = (
        get_db()
        .table("app_state")
        .update(
            {
                "current_balance": current_balance,
                "balance_synced_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .eq("id", 1)
        .execute()
    )
    return result.data[0]


def update_profile(profile: dict) -> dict:
    result = get_db().table("app_state").update({"profile": profile}).eq("id", 1).execute()
    return result.data[0]["profile"]


def adjust_balance(delta: float) -> dict:
    """Ledger-mode running update: add `delta` to current_balance.

    Deliberately does NOT touch balance_synced_at — that timestamp marks the
    last time a human confirmed the number against their real bank/cash
    balance via Balance Sync, not the last time it merely changed from
    logged activity. See docs/ARCHITECTURE.md §4.1.
    """
    current = get_app_state()
    new_balance = round(float(current["current_balance"]) + delta, 2)
    result = (
        get_db()
        .table("app_state")
        .update({"current_balance": new_balance})
        .eq("id", 1)
        .execute()
    )
    return result.data[0]


# --- transactions ---

def list_transactions(
    month: str | None = None,
    category: str | None = None,
    type_: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    query = get_db().table("transactions").select("*", count="exact")
    if month:
        start = date.fromisoformat(f"{month}-01")
        end = date(start.year + (start.month == 12), start.month % 12 + 1, 1)
        query = query.gte("date", start.isoformat()).lt("date", end.isoformat())
    if category:
        query = query.eq("category", category)
    if type_:
        query = query.eq("type", type_)
    if search:
        query = query.ilike("description", f"%{search}%")
    result = (
        query.order("date", desc=True)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return result.data, result.count or 0


def all_transactions() -> list[dict]:
    """Full history for forecasting/features (single-user scale: small)."""
    rows: list[dict] = []
    page_size = 1000
    offset = 0
    while True:
        result = (
            get_db()
            .table("transactions")
            .select("date, amount, type")
            .order("date")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows.extend(result.data)
        if len(result.data) < page_size:
            break
        offset += page_size
    return rows


def get_transaction(transaction_id: str) -> dict | None:
    result = get_db().table("transactions").select("*").eq("id", transaction_id).execute()
    return result.data[0] if result.data else None


def insert_transaction(payload: dict) -> dict:
    result = get_db().table("transactions").insert(payload).execute()
    return result.data[0]


def insert_transactions(payloads: list[dict]) -> int:
    if not payloads:
        return 0
    result = get_db().table("transactions").insert(payloads).execute()
    return len(result.data)


def update_transaction(transaction_id: str, payload: dict) -> dict | None:
    result = get_db().table("transactions").update(payload).eq("id", transaction_id).execute()
    return result.data[0] if result.data else None


def delete_transaction(transaction_id: str) -> bool:
    result = get_db().table("transactions").delete().eq("id", transaction_id).execute()
    return bool(result.data)


def month_transactions(month: str) -> list[dict]:
    start = date.fromisoformat(f"{month}-01")
    end = date(start.year + (start.month == 12), start.month % 12 + 1, 1)
    result = (
        get_db()
        .table("transactions")
        .select("amount, type, category")
        .gte("date", start.isoformat())
        .lt("date", end.isoformat())
        .execute()
    )
    return result.data


# --- BNPL plans + installments ---

def list_plans() -> list[dict]:
    result = (
        get_db()
        .table("bnpl_plans")
        .select("*, bnpl_installments(*)")
        .order("created_at", desc=True)
        .execute()
    )
    plans = []
    for row in result.data:
        installments = sorted(row.pop("bnpl_installments", []), key=lambda i: i["seq"])
        for inst in installments:
            inst["due_date"] = _parse_date(inst["due_date"])
        plans.append({**row, "installments": installments})
    return plans


def get_plan(plan_id: str) -> dict | None:
    result = (
        get_db()
        .table("bnpl_plans")
        .select("*, bnpl_installments(*)")
        .eq("id", plan_id)
        .execute()
    )
    if not result.data:
        return None
    row = result.data[0]
    installments = sorted(row.pop("bnpl_installments", []), key=lambda i: i["seq"])
    for inst in installments:
        inst["due_date"] = _parse_date(inst["due_date"])
    return {**row, "installments": installments}


def _installment_rows(plan_id: str, schedule: list[dict]) -> list[dict]:
    return [
        {
            "plan_id": plan_id,
            "seq": item["seq"],
            "due_date": item["due_date"].isoformat(),
            "amount": item["amount"],
            # An instalment charged at checkout (Atome) is already paid on the day it is due.
            **(
                {"is_paid": True, "paid_date": item["due_date"].isoformat()}
                if item.get("paid_at_checkout")
                else {}
            ),
        }
        for item in schedule
    ]


def create_plan(plan: dict, schedule: list[dict]) -> dict:
    result = get_db().table("bnpl_plans").insert(plan).execute()
    created = result.data[0]
    get_db().table("bnpl_installments").insert(_installment_rows(created["id"], schedule)).execute()
    return get_plan(created["id"])


def update_plan_fields(plan_id: str, fields: dict) -> None:
    get_db().table("bnpl_plans").update(fields).eq("id", plan_id).execute()


def list_transactions_for_plan(plan_id: str) -> list[dict]:
    """Every transaction logged by this plan's instalment payments (linked by bnpl_plan_id)."""
    result = (
        get_db()
        .table("transactions")
        .select("*")
        .eq("bnpl_plan_id", plan_id)
        .order("date")
        .order("created_at")
        .execute()
    )
    return result.data


def assert_transactions_link_column() -> None:
    """Fail fast if migration 002 was not run (paying an instalment would otherwise 500)."""
    try:
        get_db().table("transactions").select("bnpl_plan_id").limit(1).execute()
    except Exception as exc:
        raise RuntimeError(
            "transactions.bnpl_plan_id is missing. Run backend/db/migrations/002_transaction_bnpl_plan_id.sql "
            "in the Supabase SQL editor, then restart the backend."
        ) from exc


def update_plan_status(plan_id: str, status: str) -> None:
    get_db().table("bnpl_plans").update({"status": status}).eq("id", plan_id).execute()


def mark_installment_paid(plan_id: str, seq: int, paid_date: date) -> dict | None:
    result = (
        get_db()
        .table("bnpl_installments")
        .update({"is_paid": True, "paid_date": paid_date.isoformat()})
        .eq("plan_id", plan_id)
        .eq("seq", seq)
        .execute()
    )
    return result.data[0] if result.data else None


def delete_plan(plan_id: str) -> bool:
    result = get_db().table("bnpl_plans").delete().eq("id", plan_id).execute()
    return bool(result.data)


# --- risk checks ---

def insert_risk_check(record: dict) -> dict:
    result = get_db().table("risk_checks").insert(record).execute()
    return result.data[0]


def get_risk_check(check_id: str) -> dict | None:
    result = get_db().table("risk_checks").select("*").eq("id", check_id).execute()
    return result.data[0] if result.data else None


def mark_risk_check_confirmed(check_id: str, plan_id: str, original_input: dict) -> None:
    # No dedicated column in the locked schema — record confirmation inside the
    # input jsonb so a second confirm can be detected (409).
    updated_input = {**original_input, "_confirmed_plan_id": plan_id}
    get_db().table("risk_checks").update({"input": updated_input}).eq("id", check_id).execute()
