"""Idempotent seed: wipe all tables, then insert demo data (DATABASE.md §4).

    cd backend && .venv/Scripts/python scripts/seed.py

1. Transactions from farah_spending_history.xlsx (12 sheets, May 2025 - Apr 2026).
2. Two active BNPL plans with realistic Malaysian data + instalment schedules.
3. app_state: balance RM 1,850.00, default profile.
"""
import sys
from datetime import date, datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import openpyxl  # noqa: E402

from app.constants import DEFAULT_PROFILE  # noqa: E402
from app.db.client import get_db  # noqa: E402
from app.services.schedule import add_months, generate_schedule  # noqa: E402

XLSX_PATH = BACKEND_DIR.parent / "farah_spending_history.xlsx"
SEED_BALANCE = 1850.00

# Light cleanup of the sheet's hand-typed values; real personal categories are
# preserved on purpose (schema keeps category as free text).
CATEGORY_FIXES = {
    "food": "Food",
    "Self Care": "Self-Care",
}
TYPE_FIXES = {"expenses": "expense"}


def parse_xlsx() -> list[dict]:
    workbook = openpyxl.load_workbook(XLSX_PATH, data_only=True)
    rows = []
    for sheet_name in workbook.sheetnames:
        sheet = workbook[sheet_name]
        raw_rows = list(sheet.iter_rows(values_only=True))
        header_idx = next(
            (i for i, r in enumerate(raw_rows) if r and str(r[0]).strip().lower() == "type"),
            None,
        )
        if header_idx is None:
            print(f"  WARNING: sheet '{sheet_name}' has no header row; skipped")
            continue
        for raw in raw_rows[header_idx + 1:]:
            row = parse_row(raw, sheet_name)
            if row:
                rows.append(row)
    return rows


def parse_row(raw: tuple, sheet_name: str) -> dict | None:
    if not raw or not raw[0] or raw[1] is None:
        return None
    type_raw, date_raw, item, amount, category = raw[0], raw[1], raw[2], raw[3], raw[4]

    # Date cells arrive as Python datetime objects (known quirk), but guard both.
    if isinstance(date_raw, datetime):
        tx_date = date_raw.date()
    elif isinstance(date_raw, date):
        tx_date = date_raw
    else:
        print(f"  WARNING: unparseable date {date_raw!r} in '{sheet_name}'; skipped")
        return None

    if not isinstance(amount, (int, float)) or amount <= 0:
        print(f"  WARNING: bad amount {amount!r} in '{sheet_name}'; skipped")
        return None

    tx_type = str(type_raw).strip().lower()
    tx_type = TYPE_FIXES.get(tx_type, tx_type)
    if tx_type not in ("income", "expense"):
        print(f"  WARNING: unknown type {type_raw!r} in '{sheet_name}'; skipped")
        return None

    raw_category = str(category).strip() if category else "Other"
    return {
        "date": tx_date.isoformat(),
        "amount": round(float(amount), 2),
        "type": tx_type,
        "category": CATEGORY_FIXES.get(raw_category, raw_category),
        "description": str(item).strip() if item else None,
        "source": "seed",
    }


def seed_plans(db) -> tuple[int, int]:
    """Two realistic plans: one ~2 months old (2 paid), one ~3 weeks old (1 paid)."""
    today = date.today()
    plans = [
        {
            "plan": {
                "item_name": "Samsung Galaxy Buds3 Pro",
                "provider": "SPayLater",
                "total_price": 899.00,
                "interest_rate": 0,
                "num_installments": 6,
                "first_payment_date": add_months(today.replace(day=5), -2).isoformat(),
            },
            "paid": 2,
        },
        {
            "plan": {
                "item_name": "Nike Air Force 1 sneakers",
                "provider": "Atome",
                "total_price": 429.00,
                "interest_rate": 0,
                "num_installments": 3,
                "first_payment_date": add_months(today.replace(day=min(today.day, 28)), -1).isoformat(),
            },
            "paid": 1,
        },
    ]

    plan_count, inst_count = 0, 0
    for entry in plans:
        plan_data = entry["plan"]
        created = db.table("bnpl_plans").insert(plan_data).execute().data[0]
        schedule = generate_schedule(
            plan_data["total_price"],
            plan_data["interest_rate"],
            plan_data["num_installments"],
            date.fromisoformat(plan_data["first_payment_date"]),
        )
        rows = []
        for item in schedule:
            is_paid = item["seq"] <= entry["paid"]
            rows.append(
                {
                    "plan_id": created["id"],
                    "seq": item["seq"],
                    "due_date": item["due_date"].isoformat(),
                    "amount": item["amount"],
                    "is_paid": is_paid,
                    "paid_date": item["due_date"].isoformat() if is_paid else None,
                }
            )
        db.table("bnpl_installments").insert(rows).execute()
        plan_count += 1
        inst_count += len(rows)
    return plan_count, inst_count


def main() -> int:
    if not XLSX_PATH.exists():
        print(f"FAIL: {XLSX_PATH} not found")
        return 1

    db = get_db()

    print("Wiping tables...")
    db.table("risk_checks").delete().neq("label", "").execute()
    db.table("bnpl_installments").delete().gte("seq", 0).execute()
    db.table("bnpl_plans").delete().neq("item_name", "").execute()
    db.table("transactions").delete().neq("category", "").execute()

    print("Parsing xlsx...")
    transactions = parse_xlsx()
    print(f"  parsed {len(transactions)} rows")

    print("Inserting transactions...")
    batch_size = 500
    inserted = 0
    for i in range(0, len(transactions), batch_size):
        chunk = transactions[i : i + batch_size]
        db.table("transactions").insert(chunk).execute()
        inserted += len(chunk)

    print("Creating BNPL plans...")
    plan_count, inst_count = seed_plans(db)

    print("Setting app_state...")
    db.table("app_state").upsert(
        {"id": 1, "current_balance": SEED_BALANCE, "profile": DEFAULT_PROFILE}
    ).execute()

    print("\n--- Seed summary ---")
    print(f"transactions:       {inserted}")
    print(f"bnpl_plans:         {plan_count}")
    print(f"bnpl_installments:  {inst_count}")
    print(f"app_state:          balance RM {SEED_BALANCE:,.2f}, profile {DEFAULT_PROFILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
