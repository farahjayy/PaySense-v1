from datetime import date

from app.services.forecasting import (
    build_monthly_frame,
    forecast_monthly,
    low_balance_points,
    weekly_balance_curve,
)


def _six_months_transactions():
    transactions = []
    for month in range(1, 7):
        transactions.append({"date": f"2026-0{month}-05", "amount": 1200, "type": "income"})
        transactions.append({"date": f"2026-0{month}-15", "amount": 900, "type": "expense"})
    return transactions


def test_arima_with_enough_months():
    result = forecast_monthly(_six_months_transactions(), today=date(2026, 7, 1))
    assert result["method"] == "arima"
    assert len(result["months"]) == 3
    assert result["months"][0]["month"] == "2026-07"


def test_fallback_with_sparse_data_never_raises():
    sparse = [
        {"date": "2026-05-05", "amount": 1000, "type": "income"},
        {"date": "2026-06-10", "amount": 300, "type": "expense"},
    ]
    result = forecast_monthly(sparse, today=date(2026, 7, 1))
    assert result["method"] == "fallback_ma"
    assert len(result["months"]) == 3


def test_empty_transactions_fallback():
    result = forecast_monthly([], today=date(2026, 7, 1))
    assert result["method"] == "fallback_ma"
    assert all(m["net"] == 0.0 for m in result["months"])


def test_income_expense_split_difference_equals_net():
    result = forecast_monthly(_six_months_transactions(), today=date(2026, 7, 1))
    for month in result["months"]:
        assert abs((month["income"] - month["expenses"]) - month["net"]) < 0.02


def test_savings_type_excluded_from_monthly_frame():
    # A one-off savings lump must not appear as income or expense — otherwise
    # it distorts the series ARIMA is fit on (the exact bug this guards).
    transactions = [
        {"date": "2026-05-01", "amount": 1000, "type": "income"},
        {"date": "2026-05-10", "amount": 200, "type": "expense"},
        {"date": "2026-05-27", "amount": 1000, "type": "savings"},
    ]
    frame = build_monthly_frame(transactions)
    row = frame.loc["2026-05-01"]
    assert row["income"] == 1000.0
    assert row["expenses"] == 200.0
    assert row["net"] == 800.0


def test_monthly_frame_zero_fills_gap_months():
    transactions = [
        {"date": "2026-01-10", "amount": 500, "type": "income"},
        {"date": "2026-04-10", "amount": 200, "type": "expense"},
    ]
    frame = build_monthly_frame(transactions)
    assert len(frame) == 4  # Jan..Apr
    assert frame.iloc[1]["net"] == 0.0  # Feb zero-filled, not NaN


def test_balance_curve_starts_at_current_balance():
    curve = weekly_balance_curve(1850.0, [], [], today=date(2026, 7, 16))
    assert curve[0]["balance"] == 1850.0
    assert curve[0]["date"] == "2026-07-16"
    assert len(curve) == 14  # today + 13 weeks


def test_installment_lands_in_correct_week():
    installment = {"due_date": date(2026, 7, 25), "amount": 100.0}
    curve = weekly_balance_curve(500.0, [], [installment], today=date(2026, 7, 16))
    # Week 2026-07-16 → 07-23 unaffected; due date falls in week ending 07-30.
    assert curve[1]["balance"] == 500.0
    assert curve[2]["balance"] == 400.0


def test_low_balance_points_threshold():
    curve = [
        {"date": "2026-08-01", "balance": 60.0},
        {"date": "2026-08-08", "balance": 49.99},
        {"date": "2026-08-15", "balance": -10.0},
    ]
    dips = low_balance_points(curve)
    assert [p["date"] for p in dips] == ["2026-08-08", "2026-08-15"]


def test_installment_due_today_is_subtracted_in_the_first_week():
    """An instalment due on the day of the check is still owed; the weekly
    window used to be (start, end], which silently skipped it."""
    installment = {"due_date": date(2026, 7, 16), "amount": 100.0}
    curve = weekly_balance_curve(500.0, [], [installment], today=date(2026, 7, 16))
    assert curve[0]["balance"] == 500.0  # the starting point is still the synced balance
    assert curve[1]["balance"] == 400.0


def test_installment_due_today_is_not_double_counted():
    installment = {"due_date": date(2026, 7, 16), "amount": 100.0}
    curve = weekly_balance_curve(500.0, [], [installment], today=date(2026, 7, 16))
    assert curve[-1]["balance"] == 400.0


def test_installment_due_on_a_week_boundary_is_counted_once():
    installment = {"due_date": date(2026, 7, 23), "amount": 100.0}  # end of week 1 / start of week 2
    curve = weekly_balance_curve(500.0, [], [installment], today=date(2026, 7, 16))
    assert curve[1]["balance"] == 400.0
    assert curve[-1]["balance"] == 400.0
