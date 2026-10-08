"""Engine 2 artefact loading — once at startup, fail fast and loud.

Engine 2 = a Random Forest (engine2_winner.pkl, explained by SHAP) plus a
Platt-scaling calibrator (engine2_calibrator.pkl) that maps the forest's raw
P(risk) to the probability behind the 0–100 score. The calibrator is a
strictly increasing function, so it never changes which factors rank highest.

engine1_winner.pkl is provenance only and is never loaded here: ARIMA won the
evaluation, so serving refits auto_arima on the user's own data (ML_SERVING.md §1).
"""
import logging
import pickle
from functools import lru_cache

import numpy as np
import shap

from app.config import MODELS_DIR

logger = logging.getLogger("paysense")

EXPECTED_FEATURE_COUNT = 11
PROB_EPS = 1e-6  # keeps log-odds finite when a forest votes unanimously


class Engine2:
    def __init__(self, model, feature_names: list[str], explainer, calibrator):
        self.model = model
        self.feature_names = feature_names
        self.explainer = explainer
        self.calibrator = calibrator

    def calibrate(self, raw_probability: float) -> float:
        """Platt scaling: logistic fit on the log-odds of the raw forest probability."""
        clipped = min(max(raw_probability, PROB_EPS), 1 - PROB_EPS)
        log_odds = np.log(clipped / (1 - clipped))
        return float(self.calibrator.predict_proba([[log_odds]])[0, 1])


@lru_cache(maxsize=1)
def get_engine2() -> Engine2:
    feature_names = [
        str(name)
        for name in np.load(MODELS_DIR / "engine2_feature_names.npy", allow_pickle=True)
    ]
    if len(feature_names) != EXPECTED_FEATURE_COUNT:
        raise RuntimeError(
            f"engine2_feature_names.npy has {len(feature_names)} features, "
            f"expected {EXPECTED_FEATURE_COUNT}"
        )

    with open(MODELS_DIR / "engine2_winner.pkl", "rb") as f:
        model = pickle.load(f)

    with open(MODELS_DIR / "engine2_calibrator.pkl", "rb") as f:
        calibrator = pickle.load(f)

    explainer = shap.TreeExplainer(model)
    logger.info("Engine 2 loaded: %s + calibrator, features %s", type(model).__name__, feature_names)
    return Engine2(model=model, feature_names=feature_names, explainer=explainer, calibrator=calibrator)
