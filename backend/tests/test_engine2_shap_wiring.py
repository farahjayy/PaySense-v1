"""SHAP wiring checklist for the deployed Engine 2 (Random Forest + Platt).

A Random Forest is multi-output, so shap's return shape, the class index and
the raw-vs-calibrated probability distinction are all easy to get wrong
silently. These checks pin, against the real artefacts:

  1. feature order: model columns == engine.feature_names (SHAP rows are zipped
     to those names);
  2. shape: shap_values is (rows, 11, 2) and top_risk_factors takes class 1;
  3. additivity: expected_value[1] + sum(SHAP) == raw predict_proba[:, 1];
  4. calibration: strictly increasing, finite at 0/1, and predict_risk returns
     calibrate(raw) (so factor ranking is unaffected by calibration);
  5. direction: more BNPL burden / missed payments raises SHAP and raw risk;
  6. top factors: only positive contributors, ranked, from the known features.
"""
import numpy as np
import pytest

from app.services import risk as risk_svc
from app.services.features import build_feature_vector
from app.services.ml_models import get_engine2
from scripts.engine2_model_comparison import FEATURES, load_dataset

ADDITIVITY_TOLERANCE = 1e-6
SAMPLE_ROWS = 200
PROFILE = {"age": 22, "employment_status": 0}


@pytest.fixture(scope="module")
def engine():
    return get_engine2()


@pytest.fixture(scope="module")
def sample():
    df, _ = load_dataset()
    return df[FEATURES].sample(SAMPLE_ROWS, random_state=1)


def _vector(**overrides):
    kwargs = dict(
        profile=PROFILE, monthly_income=1200.0, monthly_expenses=900.0,
        active_plan_count=2, outstanding_unpaid=700.0, missed_payments=0,
        forecasted_cash_flow=250.0, proposed=None,
    )
    kwargs.update(overrides)
    return build_feature_vector(**kwargs)


def _class1_shap(engine, features) -> np.ndarray:
    return np.asarray(engine.explainer.shap_values(features))[:, :, 1]


def test_model_columns_match_engine_feature_names(engine):
    assert list(engine.model.feature_names_in_) == engine.feature_names == FEATURES


def test_shap_values_are_rows_by_features_by_classes(engine, sample):
    values = np.asarray(engine.explainer.shap_values(sample))
    assert values.shape == (len(sample), len(FEATURES), 2)


def test_shap_is_additive_over_the_raw_forest_probability(engine, sample):
    base = float(np.ravel(engine.explainer.expected_value)[1])
    reconstructed = base + _class1_shap(engine, sample).sum(axis=1)
    raw = engine.model.predict_proba(sample)[:, 1]
    assert np.abs(reconstructed - raw).max() < ADDITIVITY_TOLERANCE


def test_calibration_is_strictly_increasing(engine):
    assert engine.calibrator.coef_[0][0] > 0
    grid = np.linspace(0.0, 1.0, 101)
    calibrated = np.array([engine.calibrate(p) for p in grid])
    assert np.all(np.diff(calibrated) > 0)
    assert 0.0 < calibrated.min() and calibrated.max() < 1.0


def test_predict_risk_returns_calibrated_probability_of_the_raw_output(engine):
    vector = _vector(missed_payments=2)
    raw = float(engine.model.predict_proba(vector)[0, 1])
    probability, score, _ = risk_svc.predict_risk(engine, vector)
    assert probability == pytest.approx(engine.calibrate(raw))
    assert score == risk_svc.score_from_probability(probability)


@pytest.mark.parametrize("feature, low, high", [
    ("bnpl_income_ratio", {"outstanding_unpaid": 100.0}, {"outstanding_unpaid": 3600.0}),
    ("missed_payments", {"missed_payments": 0}, {"missed_payments": 6}),
])
def test_more_burden_raises_shap_contribution_and_raw_risk(engine, feature, low, high):
    v_low, v_high = _vector(**low), _vector(**high)
    index = engine.feature_names.index(feature)
    assert _class1_shap(engine, v_high)[0, index] > _class1_shap(engine, v_low)[0, index]
    assert engine.model.predict_proba(v_high)[0, 1] > engine.model.predict_proba(v_low)[0, 1]


def test_top_risk_factors_are_positive_ranked_known_features(engine):
    factors = risk_svc.top_risk_factors(engine, _vector(outstanding_unpaid=3600.0, missed_payments=4))
    assert 1 <= len(factors) <= risk_svc.TOP_FACTOR_COUNT
    assert [f["shap_value"] for f in factors] == sorted((f["shap_value"] for f in factors), reverse=True)
    assert all(f["shap_value"] > 0 and f["feature"] in FEATURES for f in factors)


def test_top_risk_factors_accepts_per_class_list_output():
    """Older shap versions return one array per class for multi-output models."""
    class ListExplainer:
        def shap_values(self, features):
            class0 = np.zeros((1, len(FEATURES)))
            class1 = np.arange(len(FEATURES), dtype=float).reshape(1, -1) - 5
            return [class0, class1]

    class Stub:
        feature_names = FEATURES
        explainer = ListExplainer()

    factors = risk_svc.top_risk_factors(Stub(), _vector())
    assert [f["feature"] for f in factors] == ["savings_rate", "bnpl_income_ratio", "income_expense_ratio"]


def _stub_engine(values):
    class Explainer:
        def shap_values(self, features):
            return np.array([values], dtype=float)

    class Stub:
        feature_names = FEATURES
        explainer = Explainer()

    return Stub()


def test_near_zero_factors_are_left_out_of_the_why_list():
    values = [0.0] * len(FEATURES)
    values[FEATURES.index("bnpl_outstanding")] = 0.15
    values[FEATURES.index("forecasted_cash_flow")] = risk_svc.MIN_FACTOR_SHAP - 0.001  # just under the bar
    values[FEATURES.index("age")] = 0.0107
    factors = risk_svc.top_risk_factors(_stub_engine(values), _vector())
    assert [f["feature"] for f in factors] == ["bnpl_outstanding"]


def test_a_factor_exactly_at_the_bar_is_kept():
    values = [0.0] * len(FEATURES)
    values[FEATURES.index("num_bnpl_plans")] = risk_svc.MIN_FACTOR_SHAP
    factors = risk_svc.top_risk_factors(_stub_engine(values), _vector())
    assert [f["feature"] for f in factors] == ["num_bnpl_plans"]


def test_no_factors_when_nothing_raises_the_risk_meaningfully():
    values = [-0.2] + [0.005] * (len(FEATURES) - 1)
    assert risk_svc.top_risk_factors(_stub_engine(values), _vector()) == []
