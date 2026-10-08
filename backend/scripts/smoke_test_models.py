"""Model smoke test — the canary for environment/version drift.

Loads engine2_winner.pkl + engine2_feature_names.npy, asserts the 11-feature
order, runs one dummy prediction, prints P(risk). Run before any demo:

    cd backend && .venv/Scripts/python scripts/smoke_test_models.py
"""
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

EXPECTED_FEATURES = [
    "age",
    "employment_status",
    "monthly_income",
    "monthly_expenses",
    "num_bnpl_plans",
    "bnpl_outstanding",
    "missed_payments",
    "forecasted_cash_flow",
    "income_expense_ratio",
    "bnpl_income_ratio",
    "savings_rate",
]


def main() -> int:
    feature_names = [str(f) for f in np.load(MODELS_DIR / "engine2_feature_names.npy", allow_pickle=True)]
    if feature_names != EXPECTED_FEATURES:
        print(f"FAIL: feature order mismatch.\n npy: {feature_names}\n expected: {EXPECTED_FEATURES}")
        return 1
    print(f"OK: engine2_feature_names.npy has {len(feature_names)} features in expected order")

    with open(MODELS_DIR / "engine2_winner.pkl", "rb") as f:
        model = pickle.load(f)
    print(f"OK: engine2_winner.pkl loaded ({type(model).__name__})")

    dummy = pd.DataFrame(
        [[22, 0, 1200.0, 940.0, 3, 850.0, 0, 150.0, 1.28, 0.25, 0.22]],
        columns=feature_names,
    )
    proba = model.predict_proba(dummy)[0, 1]
    print(f"OK: dummy prediction, raw P(high risk) = {proba:.4f}")

    with open(MODELS_DIR / "engine2_calibrator.pkl", "rb") as f:
        calibrator = pickle.load(f)
    log_odds = np.log(proba / (1 - proba))
    calibrated = calibrator.predict_proba([[log_odds]])[0, 1]
    print(f"OK: engine2_calibrator.pkl loaded; calibrated P(high risk) = {calibrated:.4f}")

    import shap

    explainer = shap.TreeExplainer(model)
    shap_values = np.asarray(explainer.shap_values(dummy))
    if shap_values.shape != (1, len(feature_names), 2):
        print(f"FAIL: expected SHAP shape (1, {len(feature_names)}, 2), got {shap_values.shape}")
        return 1
    reconstructed = float(np.ravel(explainer.expected_value)[1] + shap_values[0, :, 1].sum())
    if abs(reconstructed - proba) > 1e-6:
        print(f"FAIL: SHAP not additive: base + sum(shap) = {reconstructed:.6f} vs raw P = {proba:.6f}")
        return 1
    print(f"OK: SHAP shape {shap_values.shape}; base + sum(shap) reproduces raw P = {reconstructed:.6f}")
    print("SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
