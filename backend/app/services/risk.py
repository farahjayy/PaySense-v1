"""Engine 2 scoring + SHAP explanation layer (ML_SERVING.md §2–4)."""
import logging
from datetime import date

import numpy as np
import pandas as pd

from app.constants import HEALTH_CAUTION_MIN, HEALTH_SAFE_MIN, LOW_BALANCE_THRESHOLD_RM
from app.services.ml_models import Engine2

logger = logging.getLogger("paysense")

TOP_FACTOR_COUNT = 3
# SHAP values are in raw-forest probability units: 0.02 = 2 percentage points. A factor
# that adds less than this to the risk is noise, so it is not shown as a "reason".
MIN_FACTOR_SHAP = 0.02


def score_from_probability(p: float) -> int:
    return round((1 - p) * 100)


def label_from_score(score: int) -> str:
    if score >= HEALTH_SAFE_MIN:
        return "safe"
    if score >= HEALTH_CAUTION_MIN:
        return "caution"
    return "at_risk"


def predict_risk(engine: Engine2, features: pd.DataFrame) -> tuple[float, int, str]:
    """Calibrated P(risk), health score and label. SHAP (below) explains the raw
    forest output; calibration is monotone, so factor ranking is unaffected."""
    p = engine.calibrate(float(engine.model.predict_proba(features)[0, 1]))
    score = score_from_probability(p)
    return p, score, label_from_score(score)


def _format_date(iso: str) -> str:
    """dd/mm/yyyy, the app-wide date format."""
    return date.fromisoformat(iso).strftime("%d/%m/%Y")


def _format_rm(value: float) -> str:
    return f"{abs(value):,.2f}"


def _format_signed_rm(value: float) -> str:
    """'RM 709.09', or '-RM 709.09' when negative (never hide a deficit)."""
    return f"{'-' if value < 0 else ''}RM {_format_rm(value)}"


def _factor_message(feature: str, row: dict) -> str:
    income = row["monthly_income"]
    expenses = row["monthly_expenses"]
    spend_pct = round(expenses / income * 100) if income > 0 else 100
    templates = {
        "num_bnpl_plans": f"You already have {int(row['num_bnpl_plans'])} active BNPL plans (including this one)",
        "bnpl_income_ratio": f"Your total BNPL debt is {round(row['bnpl_income_ratio'] * 100)}% of your monthly income",
        "forecasted_cash_flow": (
            f"Your forecasted monthly cash flow is "
            f"{'-' if row['forecasted_cash_flow'] < 0 else '+'}RM {_format_rm(row['forecasted_cash_flow'])}"
        ),
        "missed_payments": f"You've missed {int(row['missed_payments'])} payments in the last 6 months",
        "savings_rate": f"You're currently saving {round(row['savings_rate'] * 100)}% of your income",
        "monthly_expenses": f"Your spending is {spend_pct}% of your income",
        "income_expense_ratio": f"Your spending is {spend_pct}% of your income",
        "monthly_income": f"Your monthly income is RM {_format_rm(income)}",
        "bnpl_outstanding": f"You'd owe RM {_format_rm(row['bnpl_outstanding'])} across all BNPL plans",
        "age": f"Your profile (student, {int(row['age'])}) matches a higher-risk group",
        "employment_status": f"Your profile (student, {int(row['age'])}) matches a higher-risk group",
    }
    return templates.get(feature, f"{feature} is elevating your risk")


def top_risk_factors(engine: Engine2, features: pd.DataFrame) -> list[dict]:
    """Up to 3 features pushing toward class 1 (risk) by at least MIN_FACTOR_SHAP, as plain-language rows.

    May be empty: when nothing raises the risk meaningfully there is nothing to blame."""
    shap_values = engine.explainer.shap_values(features)
    # Random Forest is multi-output: older shap returns a per-class list, newer
    # a (rows, features, classes) array. Either way take class 1 (high risk).
    values = np.asarray(shap_values[1] if isinstance(shap_values, list) else shap_values)
    if values.ndim == 3:
        values = values[:, :, 1]
    row_values = values[0]
    row = features.iloc[0].to_dict()

    ranked = sorted(
        zip(engine.feature_names, row_values),
        key=lambda item: item[1],
        reverse=True,
    )
    significant = [(f, v) for f, v in ranked if v >= MIN_FACTOR_SHAP][:TOP_FACTOR_COUNT]
    return [
        {"feature": f, "shap_value": round(float(v), 4), "message": _factor_message(f, row)}
        for f, v in significant
    ]


def low_balance_factor(with_purchase_curve: list[dict]) -> dict | None:
    """The most concrete fact the user gets — from Engine 1, not SHAP."""
    dips = [p for p in with_purchase_curve if p["balance"] < LOW_BALANCE_THRESHOLD_RM]
    if not dips:
        return None
    first = dips[0]
    pretty = _format_date(first["date"])
    return {
        "feature": "projected_balance",
        "shap_value": 0.0,
        "message": f"Your projected balance drops below RM{LOW_BALANCE_THRESHOLD_RM} on {pretty}",
    }


def build_recommendation(label: str, with_purchase_curve: list[dict], forecast_months: list[dict]) -> str:
    if label == "safe":
        return "Safe to proceed — your projected balance stays healthy."

    min_point = min(with_purchase_curve, key=lambda p: p["balance"]) if with_purchase_curve else None
    if label == "caution":
        if min_point:
            pretty = _format_date(min_point["date"])
            return (
                f"Consider delaying — your balance dips to {_format_signed_rm(min_point['balance'])} "
                f"around {pretty}."
            )
        return "Consider delaying this purchase until your cash flow improves."

    worst_month = min(forecast_months, key=lambda m: m["net"]) if forecast_months else None
    if min_point and min_point["balance"] < 0:
        month_name = date.fromisoformat(min_point["date"]).strftime("%B")
        return (
            f"Avoid this purchase — projected deficit of RM {_format_rm(min_point['balance'])} "
            f"in {month_name}."
        )
    if worst_month and worst_month["net"] < 0:
        return (
            f"Avoid this purchase — projected deficit of RM {_format_rm(worst_month['net'])} "
            f"in {worst_month['month']}."
        )
    return "Avoid this purchase — your finances can't absorb the instalments right now."
