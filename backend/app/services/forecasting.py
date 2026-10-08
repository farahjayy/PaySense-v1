"""Engine 1 — cash-flow forecasting (ML_SERVING.md §1).

ARIMA won the offline evaluation, so serving refits auto_arima on the user's
monthly net-cashflow series at request time. seasonal=False is deliberate:
the user series has <12 months, insufficient for m=12 seasonality.
"""
import logging
from datetime import date, timedelta

import pandas as pd

from app.constants import (
    FORECAST_MONTHS,
    LOW_BALANCE_THRESHOLD_RM,
    MIN_MONTHS_FOR_ARIMA,
)
from app.services.schedule import add_months

logger = logging.getLogger("paysense")

WEEKS_IN_CURVE = 13
TRAILING_MONTHS = 3


def build_monthly_frame(transactions: list[dict]) -> pd.DataFrame:
    """Aggregate transactions into per-month income/expenses/net.

    Index: month-start Timestamps covering the user's full active range;
    months with no data inside that range are 0, not NaN.
    """
    if not transactions:
        return pd.DataFrame(columns=["income", "expenses", "net"])

    df = pd.DataFrame(transactions)
    df["date"] = pd.to_datetime(df["date"])
    df["amount"] = pd.to_numeric(df["amount"])
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()

    income = df[df["type"] == "income"].groupby("month")["amount"].sum()
    expenses = df[df["type"] == "expense"].groupby("month")["amount"].sum()

    full_range = pd.date_range(df["month"].min(), df["month"].max(), freq="MS")
    frame = pd.DataFrame(index=full_range)
    frame["income"] = income.reindex(full_range, fill_value=0.0)
    frame["expenses"] = expenses.reindex(full_range, fill_value=0.0)
    frame["net"] = frame["income"] - frame["expenses"]
    return frame


def _forecast_net(net_series: pd.Series) -> tuple[str, list[float]]:
    """Return (method, 3 forecast net values). Never raises on sparse data."""
    non_empty_months = int((net_series != 0).sum())
    if len(net_series) >= MIN_MONTHS_FOR_ARIMA and non_empty_months >= MIN_MONTHS_FOR_ARIMA:
        try:
            from pmdarima import auto_arima

            model = auto_arima(
                net_series,
                seasonal=False,
                stepwise=True,
                suppress_warnings=True,
                error_action="ignore",
            )
            values = [float(v) for v in model.predict(n_periods=FORECAST_MONTHS)]
            return "arima", values
        except Exception:
            logger.warning("auto_arima failed; using moving-average fallback", exc_info=True)

    if len(net_series) == 0:
        return "fallback_ma", [0.0] * FORECAST_MONTHS
    tail = net_series.tail(TRAILING_MONTHS)
    mean_net = float(tail.mean()) if len(tail) else float(net_series.mean())
    return "fallback_ma", [mean_net] * FORECAST_MONTHS


def _split_income_expense(avg_income: float, avg_expenses: float, net: float) -> tuple[float, float]:
    """Scale the trailing averages so income − expenses == net exactly."""
    adjust = (net - (avg_income - avg_expenses)) / 2
    income = avg_income + adjust
    expenses = avg_expenses - adjust
    if income < 0:
        income, expenses = 0.0, -net
    if expenses < 0:
        income, expenses = net, 0.0
    return round(income, 2), round(expenses, 2)


def forecast_monthly(transactions: list[dict], today: date | None = None) -> dict:
    """3-month forecast: {method, months: [{month, income, expenses, net}]}."""
    today = today or date.today()
    frame = build_monthly_frame(transactions)
    method, net_values = _forecast_net(frame["net"] if len(frame) else pd.Series(dtype=float))

    if len(frame):
        avg_income = float(frame["income"].tail(TRAILING_MONTHS).mean())
        avg_expenses = float(frame["expenses"].tail(TRAILING_MONTHS).mean())
        last_month = frame.index[-1].date()
    else:
        avg_income, avg_expenses = 0.0, 0.0
        last_month = date(today.year, today.month, 1)

    months = []
    for i, net in enumerate(net_values, start=1):
        month_start = add_months(date(last_month.year, last_month.month, 1), i)
        income, expenses = _split_income_expense(avg_income, avg_expenses, net)
        months.append(
            {
                "month": month_start.strftime("%Y-%m"),
                "income": income,
                "expenses": expenses,
                "net": round(net, 2),
            }
        )
    return {"method": method, "months": months}


def weekly_balance_curve(
    current_balance: float,
    forecast_months: list[dict],
    installments: list[dict],
    today: date | None = None,
) -> list[dict]:
    """Weekly projected balance, ~3 months ahead.

    Starts at current_balance; each week adds a pro-rata share of that month's
    forecast net, then subtracts every unpaid instalment due inside the week.
    `installments`: [{due_date: date, amount: float}], unpaid only. An instalment
    due today is still owed, so the first week's window includes its start date.
    """
    today = today or date.today()
    net_by_month = {m["month"]: m["net"] for m in forecast_months}

    curve = [{"date": today.isoformat(), "balance": round(current_balance, 2)}]
    balance = current_balance
    week_start = today
    for week_index in range(WEEKS_IN_CURVE):
        week_end = week_start + timedelta(days=7)
        month_key = week_end.strftime("%Y-%m")
        net = net_by_month.get(month_key, 0.0)
        days_in_month = (add_months(date(week_end.year, week_end.month, 1), 1) - date(week_end.year, week_end.month, 1)).days
        balance += net * 7 / days_in_month
        for inst in installments:
            due = inst["due_date"]
            due_today = week_index == 0 and due == week_start
            if (week_start < due or due_today) and due <= week_end:
                balance -= float(inst["amount"])
        curve.append({"date": week_end.isoformat(), "balance": round(balance, 2)})
        week_start = week_end
    return curve


def low_balance_points(curve: list[dict]) -> list[dict]:
    return [p for p in curve if p["balance"] < LOW_BALANCE_THRESHOLD_RM]
