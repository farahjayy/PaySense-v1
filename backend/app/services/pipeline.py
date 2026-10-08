"""Sequential AI pipeline composition — Engine 1 feeds Engine 2 (ARCHITECTURE.md §2).

Also powers /api/forecast and the dashboard health score.
"""
import logging
from datetime import date

import pandas as pd

from app.constants import DEFAULT_PROFILE, FORECAST_MONTHS
from app.db import repo
from app.services import features as feat
from app.services import forecasting, plans as plan_svc, risk as risk_svc
from app.services.ml_models import get_engine2
from app.services.schedule import build_schedule, total_payable

logger = logging.getLogger("paysense")


def gather_context() -> dict:
    """One snapshot of everything the ML pipeline needs."""
    state = repo.get_app_state()
    transactions = repo.all_transactions()
    all_plans = [plan_svc.enrich_plan(p, p["installments"]) for p in repo.list_plans()]
    open_plans = [p for p in all_plans if p["status"] != "completed"]
    unpaid = [
        {
            "plan_id": p["id"],
            "due_date": inst["due_date"],
            "amount": float(inst["amount"]),
            "is_paid": inst["is_paid"],
        }
        for p in open_plans
        for inst in p["installments"]
        if not inst["is_paid"]
    ]
    return {
        "state": state,
        "profile": state.get("profile") or DEFAULT_PROFILE,
        "balance": float(state["current_balance"]),
        "transactions": transactions,
        "plans": all_plans,
        "open_plans": open_plans,
        "unpaid_installments": unpaid,
    }


def run_forecast(context: dict | None = None) -> dict:
    """GET /api/forecast payload: monthly forecast + weekly balance curve."""
    ctx = context or gather_context()
    monthly = forecasting.forecast_monthly(ctx["transactions"])
    curve = forecasting.weekly_balance_curve(ctx["balance"], monthly["months"], ctx["unpaid_installments"])
    return {
        "method": monthly["method"],
        "monthly": monthly["months"],
        "balance_curve": curve,
        "low_balance_dates": forecasting.low_balance_points(curve),
        "_months": monthly["months"],
    }


def _monthly_burden(open_plans: list[dict]) -> float:
    return sum(p["installment_amount"] for p in open_plans)


def _forecasted_cash_flow(months: list[dict], extra_installments: list[dict]) -> float:
    """Mean forecast net over the horizon, minus instalments landing in it."""
    if not months:
        return 0.0
    extra_by_month: dict[str, float] = {}
    for inst in extra_installments:
        key = inst["due_date"].strftime("%Y-%m")
        extra_by_month[key] = extra_by_month.get(key, 0.0) + float(inst["amount"])
    adjusted = [m["net"] - extra_by_month.get(m["month"], 0.0) for m in months]
    return sum(adjusted) / len(adjusted)


def run_risk_check(purchase: dict) -> dict:
    """The flagship flow: forecast → schedule overlay → features → Random Forest (calibrated) → SHAP."""
    engine = get_engine2()
    ctx = gather_context()

    monthly = forecasting.forecast_monthly(ctx["transactions"])
    purchase_date = purchase.get("purchase_date") or date.today()
    proposed_schedule = build_schedule(
        purchase["provider"],
        purchase["total_price"],
        purchase["interest_rate"],
        purchase["num_installments"],
        purchase_date,
        purchase.get("first_payment_date"),
    )
    paid_at_checkout = sum(s["amount"] for s in proposed_schedule if s["paid_at_checkout"])
    chart_schedule = [
        {
            "seq": s["seq"],
            "num_installments": purchase["num_installments"],
            "due_date": s["due_date"].isoformat(),
            "amount": s["amount"],
            "paid_at_checkout": s["paid_at_checkout"],
        }
        for s in proposed_schedule
    ]

    without_curve = forecasting.weekly_balance_curve(
        ctx["balance"], monthly["months"], ctx["unpaid_installments"]
    )
    with_curve = forecasting.weekly_balance_curve(
        ctx["balance"],
        monthly["months"],
        ctx["unpaid_installments"] + [{**s, "is_paid": False} for s in proposed_schedule],
    )

    income, expenses = feat.monthly_income_expenses(ctx["transactions"])
    all_installments = [
        {"due_date": i["due_date"], "is_paid": i["is_paid"]}
        for p in ctx["plans"]
        for i in p["installments"]
    ]
    vector = feat.build_feature_vector(
        profile=ctx["profile"],
        monthly_income=income,
        monthly_expenses=expenses,
        active_plan_count=len(ctx["open_plans"]),
        outstanding_unpaid=sum(i["amount"] for i in ctx["unpaid_installments"]),
        missed_payments=feat.count_missed_payments(all_installments),
        forecasted_cash_flow=_forecasted_cash_flow(monthly["months"], proposed_schedule),
        proposed={**purchase, "paid_at_checkout": paid_at_checkout},
    )

    probability, score, label = risk_svc.predict_risk(engine, vector)
    factors = risk_svc.top_risk_factors(engine, vector)
    dip_factor = risk_svc.low_balance_factor(with_curve)
    if dip_factor:
        factors = factors + [dip_factor]
    recommendation = risk_svc.build_recommendation(label, with_curve, monthly["months"])
    curves = {"without_purchase": without_curve, "with_purchase": with_curve, "schedule": chart_schedule}

    record = repo.insert_risk_check(
        {
            "input": {
                **purchase,
                "purchase_date": purchase_date.isoformat(),
                "fee_basis": "monthly",  # interest_rate is % per month (older checks stored a whole-plan %)
                "first_payment_date": (
                    purchase["first_payment_date"].isoformat() if purchase.get("first_payment_date") else None
                ),
            },
            "feature_vector": vector.iloc[0].to_dict(),
            "risk_probability": round(probability, 5),
            "risk_score": score,
            "label": label,
            "top_factors": factors,
            "recommendation": recommendation,
            "curves": curves,
        }
    )

    return {
        "check_id": record["id"],
        "risk_probability": round(probability, 4),
        "score": score,
        "label": label,
        "top_factors": factors,
        "recommendation": recommendation,
        "curves": curves,
        "proposed_schedule": [
            {**s, "due_date": s["due_date"].isoformat()} for s in proposed_schedule
        ],
    }


def _current_state_vector(context: dict, monthly_months: list[dict]) -> pd.DataFrame:
    """Feature vector for 'where things stand right now' — no proposed purchase on top.
    Shared by the Dashboard health gauge and run_current_risk_check, so both read the
    same number for the same state. `monthly_months` is the caller's own
    forecasting.forecast_monthly(...)["months"], so it is computed once, not per caller."""
    income, expenses = feat.monthly_income_expenses(context["transactions"])
    all_installments = [
        {"due_date": i["due_date"], "is_paid": i["is_paid"]}
        for p in context["plans"]
        for i in p["installments"]
    ]
    return feat.build_feature_vector(
        profile=context["profile"],
        monthly_income=income,
        monthly_expenses=expenses,
        active_plan_count=len(context["open_plans"]),
        outstanding_unpaid=sum(i["amount"] for i in context["unpaid_installments"]),
        missed_payments=feat.count_missed_payments(all_installments),
        forecasted_cash_flow=_forecasted_cash_flow(monthly_months, []),
        proposed=None,
    )


def dashboard_health(context: dict) -> dict:
    """Speedometer score: Engine 2 on current commitments only; rules fallback."""
    try:
        engine = get_engine2()
        monthly = forecasting.forecast_monthly(context["transactions"])
        vector = _current_state_vector(context, monthly["months"])
        _, score, label = risk_svc.predict_risk(engine, vector)
        return {"score": score, "label": label, "health_source": "model"}
    except Exception:
        logger.warning("Engine 2 health score failed; using rules fallback", exc_info=True)
        return _rules_health(context)


def run_current_risk_check(highlight_plan_id: str | None = None) -> dict:
    """Full risk check (probability + SHAP factors + balance curves) of everything currently
    committed — no proposed purchase. Used when an existing plan is added, so it gets a score
    too. Persisted as a risk_checks row so 'View full risk report' always shows this exact
    frozen snapshot, never a live recomputation. Uses the same feature vector as
    dashboard_health, so a plan's 'current risk' score matches the Dashboard health gauge for
    the same state.

    `highlight_plan_id`, when given, is excluded from the "without" curve so the balance chart
    shows specifically that plan's impact (its own instalments in vs out), the same idea as the
    pre-purchase Risk Checker's without/with-this-purchase overlay, just after the fact. The
    curve keys stay "without_purchase"/"with_purchase" for frontend reuse (OverlayChart), even
    though nothing is being purchased here.

    Marked with input.check_type='current_state' so /api/risk/confirm refuses to turn it into
    a (second, wrong) plan — see routers/risk.py.
    """
    engine = get_engine2()
    ctx = gather_context()
    monthly = forecasting.forecast_monthly(ctx["transactions"])
    vector = _current_state_vector(ctx, monthly["months"])
    probability, score, label = risk_svc.predict_risk(engine, vector)
    factors = risk_svc.top_risk_factors(engine, vector)
    recommendation = risk_svc.current_state_recommendation(label)

    with_curve = forecasting.weekly_balance_curve(ctx["balance"], monthly["months"], ctx["unpaid_installments"])
    without_installments = (
        [i for i in ctx["unpaid_installments"] if i["plan_id"] != highlight_plan_id]
        if highlight_plan_id
        else ctx["unpaid_installments"]
    )
    without_curve = forecasting.weekly_balance_curve(ctx["balance"], monthly["months"], without_installments)
    highlight_plan = next((p for p in ctx["plans"] if p["id"] == highlight_plan_id), None)
    chart_schedule = (
        [
            {
                "seq": i["seq"],
                "num_installments": highlight_plan["num_installments"],
                "due_date": i["due_date"].isoformat(),
                "amount": float(i["amount"]),
                # Always False: a checkout-paid instalment (e.g. Atome's first) is already
                # marked is_paid and excluded by the filter below, so it never reaches here.
                "paid_at_checkout": False,
            }
            for i in highlight_plan["installments"]
            if not i["is_paid"]
        ]
        if highlight_plan
        else []
    )
    curves = {"without_purchase": without_curve, "with_purchase": with_curve, "schedule": chart_schedule}

    record = repo.insert_risk_check(
        {
            "input": {"check_type": "current_state", "highlight_plan_id": highlight_plan_id},
            "feature_vector": vector.iloc[0].to_dict(),
            "risk_probability": round(probability, 5),
            "risk_score": score,
            "label": label,
            "top_factors": factors,
            "recommendation": recommendation,
            "curves": curves,
        }
    )
    return {
        "check_id": record["id"],
        "risk_probability": round(probability, 4),
        "score": score,
        "label": label,
        "top_factors": factors,
        "recommendation": recommendation,
        "curves": curves,
    }


def _rules_health(context: dict) -> dict:
    """Degraded score from income/expense ratio + BNPL burden — never blank."""
    income, expenses = feat.monthly_income_expenses(context["transactions"])
    burden = _monthly_burden(context["open_plans"])
    savings_rate = (income - expenses) / income if income > 0 else 0.0
    burden_ratio = burden / income if income > 0 else (1.0 if burden > 0 else 0.0)
    savings_component = max(0.0, min(savings_rate, 0.4)) / 0.4 * 60
    burden_component = (1 - max(0.0, min(burden_ratio, 0.5)) / 0.5) * 40
    score = round(savings_component + burden_component)
    return {"score": score, "label": risk_svc.label_from_score(score), "health_source": "rules"}
