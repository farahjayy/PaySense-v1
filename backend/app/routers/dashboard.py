"""One aggregate call powering the whole dashboard screen."""
import logging
from datetime import date, timedelta

from fastapi import APIRouter

from app.constants import ALERT_WINDOW_DAYS, HISTORY_MONTHS_SHOWN
from app.services import forecasting, pipeline

logger = logging.getLogger("paysense")
router = APIRouter(prefix="/api", tags=["dashboard"])


def _history_chart(transactions: list[dict], today: date) -> list[dict]:
    frame = forecasting.build_monthly_frame(transactions)
    entries = []
    for ts, row in frame.tail(HISTORY_MONTHS_SHOWN).iterrows():
        entries.append(
            {
                "month": ts.strftime("%Y-%m"),
                "income": round(float(row["income"]), 2),
                "expenses": round(float(row["expenses"]), 2),
                "is_forecast": False,
            }
        )
    return entries


def _bnpl_summary(open_plans: list[dict], today: date) -> dict:
    """Total unpaid across all open plans, split into overdue (due date already passed) and
    upcoming (everything else still owed)."""
    overdue = upcoming = 0.0
    for plan in open_plans:
        for inst in plan["installments"]:
            if inst["is_paid"]:
                continue
            if inst["due_date"] < today:
                overdue += float(inst["amount"])
            else:
                upcoming += float(inst["amount"])
    return {"plan_count": len(open_plans), "overdue_total": round(overdue, 2), "upcoming_total": round(upcoming, 2)}


def _alerts(context: dict, balance_curve: list[dict], today: date) -> list[dict]:
    window_end = today + timedelta(days=ALERT_WINDOW_DAYS)
    alerts = []
    for plan in context["open_plans"]:
        for inst in plan["installments"]:
            if inst["is_paid"] or not (today <= inst["due_date"] <= window_end):
                continue
            projected = next(
                (p["balance"] for p in balance_curve if date.fromisoformat(p["date"]) >= inst["due_date"]),
                context["balance"],
            )
            alerts.append(
                {
                    "plan_id": plan["id"],
                    "item_name": plan["item_name"],
                    "amount": float(inst["amount"]),
                    "due_date": inst["due_date"].isoformat(),
                    "projected_balance_sufficient": projected >= 0,
                }
            )
    return sorted(alerts, key=lambda a: a["due_date"])


@router.get("/dashboard")
def get_dashboard():
    today = date.today()
    context = pipeline.gather_context()
    forecast = pipeline.run_forecast(context)
    health = pipeline.dashboard_health(context)

    month_key = today.strftime("%Y-%m")
    month_rows = [t for t in context["transactions"] if str(t["date"])[:7] == month_key]
    month_income = sum(float(t["amount"]) for t in month_rows if t["type"] == "income")
    month_expenses = sum(float(t["amount"]) for t in month_rows if t["type"] == "expense")

    chart = _history_chart(context["transactions"], today) + [
        {
            "month": m["month"],
            "income": m["income"],
            "expenses": m["expenses"],
            "is_forecast": True,
        }
        for m in forecast["monthly"]
    ]

    active_plans = sorted(
        (
            {
                "id": p["id"],
                "item_name": p["item_name"],
                "provider": p["provider"],
                "status": p["status"],
                "installment_amount": p["installment_amount"],
                "remaining_total": round(
                    sum(float(i["amount"]) for i in p["installments"] if not i["is_paid"]), 2
                ),
                "paid_count": p["paid_count"],
                "num_installments": p["num_installments"],
                "remaining_installments": p["remaining_count"],
                "next_due_date": p["next_due_date"],
            }
            for p in context["open_plans"]
        ),
        # Soonest/most overdue due date first; a plan with nothing left due sorts last.
        key=lambda p: p["next_due_date"] or "9999-99-99",
    )

    state = context["state"]
    return {
        "current_balance": context["balance"],
        "balance_synced_at": state["balance_synced_at"],
        "month_summary": {
            "income": round(month_income, 2),
            "expenses": round(month_expenses, 2),
            "month": month_key,
        },
        "health": health,
        "chart": chart,
        "forecast_method": forecast["method"],
        "active_plans": active_plans,
        "bnpl_summary": _bnpl_summary(context["open_plans"], today),
        "alerts": _alerts(context, forecast["balance_curve"], today),
    }
