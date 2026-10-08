"""Consistency invariant: the risk score shown to the user and the SHAP
"why" factors shown alongside it must come from the exact same feature
vector. If a future refactor rebuilds the vector separately for the SHAP
call, the two could silently desync (e.g. forgetting to include the
proposed purchase the second time) without either call raising an error."""
from datetime import date

import pandas as pd

from app.services import pipeline


def _purchase(**overrides):
    kwargs = dict(
        item_name="iphone 16e",
        total_price=5000.0,
        provider="SPayLater",
        num_installments=6,
        interest_rate=3.0,
        first_payment_date=date.today(),
    )
    kwargs.update(overrides)
    return kwargs


def test_run_risk_check_uses_same_vector_for_prediction_and_shap(store, monkeypatch):
    recorded = []

    real_predict_risk = pipeline.risk_svc.predict_risk
    real_top_risk_factors = pipeline.risk_svc.top_risk_factors

    def spy_predict_risk(engine, features):
        recorded.append(features)
        return real_predict_risk(engine, features)

    def spy_top_risk_factors(engine, features):
        recorded.append(features)
        return real_top_risk_factors(engine, features)

    monkeypatch.setattr(pipeline.risk_svc, "predict_risk", spy_predict_risk)
    monkeypatch.setattr(pipeline.risk_svc, "top_risk_factors", spy_top_risk_factors)

    pipeline.run_risk_check(_purchase())

    assert len(recorded) == 2
    pd.testing.assert_frame_equal(recorded[0], recorded[1])


def test_dashboard_health_uses_same_vector_for_prediction_and_shap(store, monkeypatch):
    recorded = []
    real_predict_risk = pipeline.risk_svc.predict_risk

    def spy_predict_risk(engine, features):
        recorded.append(features)
        return real_predict_risk(engine, features)

    monkeypatch.setattr(pipeline.risk_svc, "predict_risk", spy_predict_risk)

    context = pipeline.gather_context()
    pipeline.dashboard_health(context)

    assert len(recorded) == 1


def test_dashboard_health_vector_excludes_proposed_purchase(store, monkeypatch):
    """dashboard_health always passes proposed=None — the dashboard score
    reflects current commitments only, never a hypothetical purchase
    (that's what the separate Risk Checker flow is for)."""
    recorded = []
    real_predict_risk = pipeline.risk_svc.predict_risk

    def spy_predict_risk(engine, features):
        recorded.append(features)
        return real_predict_risk(engine, features)

    monkeypatch.setattr(pipeline.risk_svc, "predict_risk", spy_predict_risk)

    context = pipeline.gather_context()
    pipeline.dashboard_health(context)

    vector = recorded[0].iloc[0]
    assert vector["num_bnpl_plans"] == len(context["open_plans"])
    assert vector["bnpl_outstanding"] == round(sum(i["amount"] for i in context["unpaid_installments"]), 2)
