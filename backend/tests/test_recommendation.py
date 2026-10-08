"""build_recommendation must not hide a negative projected balance."""
from app.services.risk import build_recommendation, low_balance_factor

MONTHS = [{"month": "2026-10", "net": 10.0}]


def _curve(balance: float) -> list[dict]:
    return [
        {"date": "2026-11-06", "balance": 1000.0},
        {"date": "2026-12-25", "balance": balance},
    ]


def test_caution_message_shows_minus_sign_for_a_negative_balance():
    message = build_recommendation("caution", _curve(-709.09), MONTHS)
    assert "-RM 709.09" in message
    assert "25/12/2026" in message


def test_caution_message_unchanged_for_a_positive_balance():
    message = build_recommendation("caution", _curve(709.09), MONTHS)
    assert "dips to RM 709.09" in message
    assert "-RM" not in message


def test_projected_dates_use_dd_mm_yyyy():
    assert "on 27/11/2026" in low_balance_factor([{"date": "2026-11-27", "balance": 10.0}])["message"]


def test_bnpl_ratio_message_describes_total_debt_not_the_instalment():
    from app.services.features import build_feature_vector
    from app.services.risk import _factor_message

    proposed = {"total_price": 5000.0, "interest_rate": 0.5, "num_installments": 6}  # 5,150 payable
    row = build_feature_vector(
        profile={"age": 22, "employment_status": 0}, monthly_income=1000.0, monthly_expenses=870.0,
        active_plan_count=0, outstanding_unpaid=0.0, missed_payments=0, forecasted_cash_flow=0.0,
        proposed=proposed,
    ).iloc[0].to_dict()
    assert _factor_message("bnpl_income_ratio", row) == "Your total BNPL debt is 515% of your monthly income"
