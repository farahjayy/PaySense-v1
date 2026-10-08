"""Engine 2 label-fix verification (see docs/KNOWN_LIMITATIONS.md).

The v1/v2 synthetic training label used hard binary thresholds:
missed_payments only counted at >=2, and bnpl_income_ratio was a flat +2
whether it was 51% or 500% of income. A real Risk Checker case (iPhone 16e,
RM5000, SPayLater, 6 instalments) exposed this: 115% of income scored
"safe" (P(risk)=0.08) because missed_payments=1 got zero label credit and
swamped bnpl_income_ratio's contribution in SHAP (-3.13 vs +1.13).

paysense_engine2_classification.ipynb was retrained (2026-09-16) with a
continuous-scaling label (linear ramps instead of cliffs/plateaus). These
tests pin the *fixed* model's behaviour so a future retrain that
reintroduces the old cliff/plateau pattern fails loudly.
"""
from app.services.features import build_feature_vector
from app.services.ml_models import get_engine2
from app.services import risk as risk_svc

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


def test_missed_payments_contributes_below_old_threshold():
    """0->1 missed payment must now move the score — the old label gave it
    zero credit below the >=2 cliff, which SHAP traced to a -3.13
    contribution overriding everything else."""
    engine = get_engine2()
    probs = []
    for m in range(7):
        p, _, _ = risk_svc.predict_risk(engine, _vector(missed_payments=m))
        probs.append(p)

    # Non-decreasing across the whole sweep (holds for the retrained model).
    assert all(b >= a - 1e-9 for a, b in zip(probs, probs[1:])), probs
    # The specific gap the old model got wrong: 0->1 must be a real delta,
    # not the near-zero step the >=2 cliff used to produce.
    assert probs[1] - probs[0] > 0.005, f"0->1 missed_payments barely moved risk: {probs}"


def test_bnpl_income_ratio_no_longer_flat_above_threshold():
    """Old label gave bnpl_income_ratio a flat +2 for any value over 0.5,
    so 51% and 300%+ of income read as identical risk. Tree ensembles
    aren't guaranteed strictly monotonic, so we check the *range* isn't
    flat rather than every intermediate step."""
    engine = get_engine2()
    low, _, _ = risk_svc.predict_risk(engine, _vector(outstanding_unpaid=600.0))    # ratio 0.5 (income 1200)
    high, _, _ = risk_svc.predict_risk(engine, _vector(outstanding_unpaid=3600.0))  # ratio 3.0
    assert high - low > 0.3, (
        f"bnpl_income_ratio 0.5->3.0 barely moved risk (low={low:.4f}, high={high:.4f}) "
        "— looks like the old flat-plateau behaviour is back"
    )


def test_high_burden_scenario_no_longer_reads_safe():
    """The exact iPhone-16e/RM5000/SPayLater/6-instalment scenario that
    surfaced this issue, re-verified against the retrained model via the
    live /api/risk/check call on 2026-09-16 (check_id
    54fbf067-3909-47ae-8fe8-3006eb48ff98)."""
    engine = get_engine2()
    vector = build_feature_vector(
        profile=PROFILE,
        monthly_income=1000.0,
        monthly_expenses=963.1,
        active_plan_count=2,
        outstanding_unpaid=885.34,  # existing unpaid installments; + proposed 5000*1.03 = 6035.34
        missed_payments=2,
        forecasted_cash_flow=45.99,
        # 0.5% per month x 6 months = the 3% whole-plan fee this historical scenario was run with.
        proposed={"total_price": 5000.0, "interest_rate": 0.5, "num_installments": 6},
    )
    row = vector.iloc[0]
    assert row["bnpl_income_ratio"] == 6.0353  # total debt 6,035.34 / income 1,000
    assert row["bnpl_outstanding"] == 6035.34

    # Pinned to the deployed Random Forest + Platt calibration.
    # History: binary-threshold LightGBM 0.0802 / "safe" (the bug) -> continuous-
    # label LightGBM 0.4094 / score 59 / "caution" -> Random Forest + Platt 0.6242 /
    # score 38 -> bnpl_income_ratio served as total debt / income (as trained, 6.04
    # instead of 1.15) 0.7636 / score 24.
    probability, score, label = risk_svc.predict_risk(engine, vector)
    assert abs(probability - 0.76357) < 1e-3, probability
    assert score == 24
    assert label == "at_risk"
    assert label != "safe", "regression: this scenario scored 'safe' under the old binary-threshold label"
