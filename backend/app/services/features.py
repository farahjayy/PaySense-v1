"""Engine 2 feature engineering — 11 features in the exact npy order (ML_SERVING.md §2).

employment_status encoding is fixed by training and must never change:
0=student, 1=employed, 2=self-employed, 3=unemployed.
"""
from datetime import date

import pandas as pd

from app.constants import RATIO_CAP
from app.services.schedule import add_months, total_payable

FEATURE_ORDER = [
    "age",
    "employment_status",
    "monthly_income",
    "monthly_expenses",
    "num_bnpl_plans",
    "bnpl_outstanding",
    "missed_payments",
    "forecasted_cash_flow",
    "income_expense_ratio",
    "bnpl_income_ratio",
    "savings_rate",
]

TRAILING_MONTHS = 3
MISSED_WINDOW_MONTHS = 6


def _safe_ratio(numerator: float, denominator: float, zero_value: float) -> float:
    """Div-by-zero guard: capped, finite ratios when the denominator is 0."""
    if denominator <= 0:
        return zero_value if numerator <= 0 else RATIO_CAP
    return min(numerator / denominator, RATIO_CAP)


def monthly_income_expenses(transactions: list[dict], today: date | None = None) -> tuple[float, float]:
    """Mean monthly income/expenses over the last 3 full months of data."""
    today = today or date.today()
    if not transactions:
        return 0.0, 0.0
    df = pd.DataFrame(transactions)
    df["date"] = pd.to_datetime(df["date"])
    df["amount"] = pd.to_numeric(df["amount"])
    current_month = pd.Timestamp(today.year, today.month, 1)
    df = df[df["date"] < current_month]  # full months only
    if df.empty:
        return 0.0, 0.0
    df["month"] = df["date"].dt.to_period("M")
    months = sorted(df["month"].unique())[-TRAILING_MONTHS:]
    window = df[df["month"].isin(months)]
    income = window[window["type"] == "income"].groupby("month")["amount"].sum()
    expenses = window[window["type"] == "expense"].groupby("month")["amount"].sum()
    n = len(months)
    return float(income.sum()) / n, float(expenses.sum()) / n


def count_missed_payments(installments: list[dict], today: date | None = None) -> int:
    """Overdue = unpaid and past due, within the last 6 months."""
    today = today or date.today()
    window_start = add_months(today, -MISSED_WINDOW_MONTHS)
    return sum(
        1
        for inst in installments
        if not inst["is_paid"] and window_start <= inst["due_date"] < today
    )


def build_feature_vector(
    profile: dict,
    monthly_income: float,
    monthly_expenses: float,
    active_plan_count: int,
    outstanding_unpaid: float,
    missed_payments: int,
    forecasted_cash_flow: float,
    proposed: dict | None = None,
) -> pd.DataFrame:
    """Single-row DataFrame in FEATURE_ORDER.

    `proposed` (the purchase under evaluation) adds 1 plan and its total payable
    to the outstanding amount. Any `paid_at_checkout` amount (Atome's first
    payment) is already paid, so it is not outstanding.

    `bnpl_income_ratio` is total BNPL debt / monthly income (bnpl_outstanding /
    monthly_income) - the definition the model was trained on (notebook cell 7),
    NOT the monthly instalment over income.
    `forecasted_cash_flow` must already reflect the with-purchase forecast.
    """
    num_plans = active_plan_count
    outstanding = outstanding_unpaid
    if proposed is not None:
        payable = total_payable(proposed["total_price"], proposed["interest_rate"], proposed["num_installments"])
        num_plans += 1
        outstanding += payable - proposed.get("paid_at_checkout", 0.0)

    if monthly_income > 0:
        # May legitimately be negative (overspending); clamp to a finite band.
        savings = max(min((monthly_income - monthly_expenses) / monthly_income, 1.0), -RATIO_CAP)
    else:
        savings = 0.0
    row = {
        "age": profile.get("age", 22),
        "employment_status": profile.get("employment_status", 0),
        "monthly_income": round(monthly_income, 2),
        "monthly_expenses": round(monthly_expenses, 2),
        "num_bnpl_plans": num_plans,
        "bnpl_outstanding": round(outstanding, 2),
        "missed_payments": missed_payments,
        "forecasted_cash_flow": round(forecasted_cash_flow, 2),
        "income_expense_ratio": round(_safe_ratio(monthly_income, monthly_expenses, zero_value=RATIO_CAP), 4),
        "bnpl_income_ratio": round(_safe_ratio(outstanding, monthly_income, zero_value=0.0), 4),
        "savings_rate": round(savings, 4),
    }
    return pd.DataFrame([row], columns=FEATURE_ORDER)
