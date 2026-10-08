"""Integration-test fixtures: an in-memory fake of the repo layer so API
round-trips run without a live Supabase project. The real ML artefacts ARE
used — only data access is faked."""
import uuid
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.db import repo
from app.main import app


class FakeStore:
    def __init__(self):
        today = date.today()
        self.app_state = {
            "id": 1,
            "current_balance": 1850.00,
            "balance_synced_at": datetime.now(timezone.utc).isoformat(),
            "profile": {"age": 22, "employment_status": 0},
            "ledger_mode": False,
        }
        self.transactions: list[dict] = []
        self.plans: list[dict] = []
        self.risk_checks: list[dict] = []
        # Six months of history so ARIMA has enough data.
        for offset in range(6, 0, -1):
            month = _add_months(today.replace(day=1), -offset)
            self.transactions.append(_tx(month.replace(day=5), 1200.0, "income", "Allowance"))
            self.transactions.append(_tx(month.replace(day=15), 900.0, "expense", "Food"))


def _add_months(start: date, months: int) -> date:
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def _tx(tx_date: date, amount: float, type_: str, category: str) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "date": tx_date.isoformat(),
        "amount": amount,
        "type": type_,
        "category": category,
        "description": None,
        "account_name": None,
        "is_bnpl": False,
        "source": "seed",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture()
def store(monkeypatch) -> FakeStore:
    fake = FakeStore()

    def list_transactions(month=None, category=None, type_=None, search=None, limit=50, offset=0):
        rows = list(fake.transactions)
        if month:
            rows = [r for r in rows if r["date"][:7] == month]
        if category:
            rows = [r for r in rows if r["category"] == category]
        if type_:
            rows = [r for r in rows if r["type"] == type_]
        if search:
            rows = [r for r in rows if search.lower() in (r["description"] or "").lower()]
        total = len(rows)
        rows.sort(key=lambda r: r["date"], reverse=True)
        return rows[offset : offset + limit], total

    def insert_transaction(payload):
        row = {**_tx(date.fromisoformat(payload["date"]), payload["amount"], payload["type"], payload["category"]), **payload}
        fake.transactions.append(row)
        return row

    def insert_transactions(payloads):
        for p in payloads:
            insert_transaction(p)
        return len(payloads)

    def get_transaction(transaction_id):
        for row in fake.transactions:
            if row["id"] == transaction_id:
                return dict(row)
        return None

    def update_transaction(transaction_id, payload):
        for i, row in enumerate(fake.transactions):
            if row["id"] == transaction_id:
                fake.transactions[i] = {**row, **payload}
                return fake.transactions[i]
        return None

    def adjust_balance(delta):
        fake.app_state["current_balance"] = round(fake.app_state["current_balance"] + delta, 2)
        return fake.app_state

    def delete_transaction(transaction_id):
        before = len(fake.transactions)
        fake.transactions = [r for r in fake.transactions if r["id"] != transaction_id]
        return len(fake.transactions) < before

    def month_transactions(month):
        return [r for r in fake.transactions if r["date"][:7] == month]

    def all_transactions():
        return [{"date": r["date"], "amount": r["amount"], "type": r["type"]} for r in fake.transactions]

    def list_plans():
        return [_clone_plan(p) for p in fake.plans]

    def get_plan(plan_id):
        for p in fake.plans:
            if p["id"] == plan_id:
                return _clone_plan(p)
        return None

    def create_plan(plan, schedule):
        plan_id = str(uuid.uuid4())
        stored = {
            **plan,
            "id": plan_id,
            "status": "active",
            "risk_score_at_creation": plan.get("risk_score_at_creation"),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "installments": [
                {
                    "id": str(uuid.uuid4()),
                    "plan_id": plan_id,
                    "seq": item["seq"],
                    "due_date": item["due_date"],
                    "amount": item["amount"],
                    "is_paid": bool(item.get("paid_at_checkout")),
                    "paid_date": item["due_date"].isoformat() if item.get("paid_at_checkout") else None,
                }
                for item in schedule
            ],
        }
        fake.plans.append(stored)
        return _clone_plan(stored)

    def list_transactions_for_plan(plan_id):
        return [dict(r) for r in fake.transactions if r.get("bnpl_plan_id") == plan_id]

    def update_plan_fields(plan_id, fields):
        for p in fake.plans:
            if p["id"] == plan_id:
                p.update(fields)

    def update_plan_status(plan_id, status):
        for p in fake.plans:
            if p["id"] == plan_id:
                p["status"] = status

    def mark_installment_paid(plan_id, seq, paid_date):
        for p in fake.plans:
            if p["id"] == plan_id:
                for inst in p["installments"]:
                    if inst["seq"] == seq:
                        inst["is_paid"] = True
                        inst["paid_date"] = paid_date.isoformat()
                        return inst
        return None

    def delete_plan(plan_id):
        before = len(fake.plans)
        fake.plans = [p for p in fake.plans if p["id"] != plan_id]
        return len(fake.plans) < before

    def insert_risk_check(record):
        stored = {**record, "id": str(uuid.uuid4()), "created_at": datetime.now(timezone.utc).isoformat()}
        fake.risk_checks.append(stored)
        return stored

    def get_risk_check(check_id):
        for check in fake.risk_checks:
            if check["id"] == check_id:
                return check
        return None

    def mark_risk_check_confirmed(check_id, plan_id, original_input):
        for check in fake.risk_checks:
            if check["id"] == check_id:
                check["input"] = {**original_input, "_confirmed_plan_id": plan_id}

    monkeypatch.setattr(repo, "get_app_state", lambda: fake.app_state)
    monkeypatch.setattr(repo, "update_balance", lambda balance: {**fake.app_state, "current_balance": balance})
    monkeypatch.setattr(repo, "adjust_balance", adjust_balance)
    def update_profile(profile):
        fake.app_state["profile"] = profile
        return profile

    monkeypatch.setattr(repo, "update_profile", update_profile)
    monkeypatch.setattr(repo, "list_transactions", list_transactions)
    monkeypatch.setattr(repo, "insert_transaction", insert_transaction)
    monkeypatch.setattr(repo, "insert_transactions", insert_transactions)
    monkeypatch.setattr(repo, "get_transaction", get_transaction)
    monkeypatch.setattr(repo, "update_transaction", update_transaction)
    monkeypatch.setattr(repo, "delete_transaction", delete_transaction)
    monkeypatch.setattr(repo, "month_transactions", month_transactions)
    monkeypatch.setattr(repo, "all_transactions", all_transactions)
    monkeypatch.setattr(repo, "list_plans", list_plans)
    monkeypatch.setattr(repo, "get_plan", get_plan)
    monkeypatch.setattr(repo, "create_plan", create_plan)
    monkeypatch.setattr(repo, "update_plan_status", update_plan_status)
    monkeypatch.setattr(repo, "update_plan_fields", update_plan_fields)
    monkeypatch.setattr(repo, "list_transactions_for_plan", list_transactions_for_plan)
    monkeypatch.setattr(repo, "mark_installment_paid", mark_installment_paid)
    monkeypatch.setattr(repo, "delete_plan", delete_plan)
    monkeypatch.setattr(repo, "insert_risk_check", insert_risk_check)
    monkeypatch.setattr(repo, "get_risk_check", get_risk_check)
    monkeypatch.setattr(repo, "mark_risk_check_confirmed", mark_risk_check_confirmed)
    return fake


def _clone_plan(plan: dict) -> dict:
    return {**plan, "installments": [dict(inst) for inst in plan["installments"]]}


@pytest.fixture()
def client(store) -> TestClient:
    # No context manager: lifespan (env validation) is skipped; the fake repo
    # replaces all DB access and the real model loads lazily.
    return TestClient(app, raise_server_exceptions=False)
