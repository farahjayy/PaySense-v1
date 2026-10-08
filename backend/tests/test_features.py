from datetime import date
from pathlib import Path

import numpy as np

from app.services.features import (
    FEATURE_ORDER,
    build_feature_vector,
    count_missed_payments,
    monthly_income_expenses,
)

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

PROFILE = {"age": 22, "employment_status": 0}


def _vector(**overrides):
    kwargs = dict(
        profile=PROFILE,
        monthly_income=1200.0,
        monthly_expenses=900.0,
        active_plan_count=2,
        outstanding_unpaid=700.0,
        missed_payments=0,
        forecasted_cash_flow=250.0,
        proposed=None,
    )
    kwargs.update(overrides)
    return build_feature_vector(**kwargs)


def test_order_matches_npy():
    npy = [str(f) for f in np.load(MODELS_DIR / "engine2_feature_names.npy", allow_pickle=True)]
    assert FEATURE_ORDER == npy
    assert list(_vector().columns) == npy


def test_employment_status_encoding_passthrough():
    # 0=student, 1=employed, 2=self-employed, 3=unemployed — fixed by training.
    for code in (0, 1, 2, 3):
        vector = _vector(profile={"age": 24, "employment_status": code})
        assert vector.iloc[0]["employment_status"] == code


def test_proposed_purchase_increments_plans_and_outstanding():
    # 10% per month x 6 months = 60% on top of the price -> 960 payable
    proposed = {"total_price": 600.0, "interest_rate": 10.0, "num_installments": 6}
    base = _vector().iloc[0]
    with_proposed = _vector(proposed=proposed).iloc[0]
    assert with_proposed["num_bnpl_plans"] == base["num_bnpl_plans"] + 1
    assert with_proposed["bnpl_outstanding"] == round(base["bnpl_outstanding"] + 960.0, 2)
    assert with_proposed["bnpl_income_ratio"] > base["bnpl_income_ratio"]


def test_zero_income_ratios_are_finite_and_capped():
    row = _vector(monthly_income=0.0, monthly_expenses=500.0).iloc[0]
    assert np.isfinite(row["income_expense_ratio"])
    assert np.isfinite(row["bnpl_income_ratio"])
    assert np.isfinite(row["savings_rate"])
    assert row["savings_rate"] == 0.0


def test_zero_expenses_ratio_capped():
    row = _vector(monthly_expenses=0.0).iloc[0]
    assert np.isfinite(row["income_expense_ratio"])
    assert row["income_expense_ratio"] <= 10.0


def test_forecasted_cash_flow_passthrough():
    # Engine 1 linkage: value is computed on the with-purchase forecast upstream.
    row = _vector(forecasted_cash_flow=-123.45).iloc[0]
    assert row["forecasted_cash_flow"] == -123.45


def test_monthly_income_expenses_last_three_full_months():
    today = date(2026, 7, 16)
    transactions = []
    for month in (4, 5, 6):
        transactions.append({"date": f"2026-0{month}-05", "amount": 1000, "type": "income"})
        transactions.append({"date": f"2026-0{month}-10", "amount": 400, "type": "expense"})
    # Current (partial) month must be excluded:
    transactions.append({"date": "2026-07-01", "amount": 9999, "type": "income"})
    income, expenses = monthly_income_expenses(transactions, today=today)
    assert income == 1000.0
    assert expenses == 400.0


def test_count_missed_payments_window():
    today = date(2026, 7, 16)
    installments = [
        {"due_date": date(2026, 6, 1), "is_paid": False},   # missed, in window
        {"due_date": date(2026, 5, 1), "is_paid": True},    # paid
        {"due_date": date(2025, 11, 1), "is_paid": False},  # older than 6 months
        {"due_date": date(2026, 8, 1), "is_paid": False},   # future
    ]
    assert count_missed_payments(installments, today=today) == 1


def test_payment_made_at_checkout_is_not_outstanding():
    proposed = {"total_price": 300.0, "interest_rate": 0.0, "num_installments": 3}
    base = _vector().iloc[0]
    prepaid = _vector(proposed={**proposed, "paid_at_checkout": 100.0}).iloc[0]
    assert prepaid["bnpl_outstanding"] == round(base["bnpl_outstanding"] + 200.0, 2)
    # The ratio is total debt / income, so the prepaid part drops out of it too.
    assert prepaid["bnpl_income_ratio"] == round(prepaid["bnpl_outstanding"] / prepaid["monthly_income"], 4)
    assert prepaid["bnpl_income_ratio"] < _vector(proposed=proposed).iloc[0]["bnpl_income_ratio"]


def test_bnpl_income_ratio_is_total_bnpl_debt_over_income():
    """Matches the training definition (bnpl_outstanding / monthly_income), not the monthly instalment."""
    row = _vector(monthly_income=1000.0, outstanding_unpaid=1200.0).iloc[0]
    assert row["bnpl_outstanding"] == 1200.0
    assert row["bnpl_income_ratio"] == 1.2


def test_bnpl_income_ratio_includes_the_purchase_being_checked():
    proposed = {"total_price": 5000.0, "interest_rate": 0.5, "num_installments": 6}  # 5,150 payable
    row = _vector(monthly_income=1000.0, outstanding_unpaid=885.34, proposed=proposed).iloc[0]
    assert row["bnpl_outstanding"] == 6035.34
    assert row["bnpl_income_ratio"] == 6.0353
