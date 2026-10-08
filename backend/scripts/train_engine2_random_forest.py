"""Train + export the deployed Engine 2 model: Random Forest + Platt calibration.

Chosen after scripts/engine2_model_comparison.py (docs/KNOWN_LIMITATIONS.md):
Random Forest beat XGBoost and LightGBM on ROC-AUC and Brier score, and among
calibration methods sigmoid (Platt on log-odds) beat isotonic. All three
candidates used hand-set, untuned hyperparameters.

What is exported
  engine2_winner.pkl      the raw, SMOTE-trained Random Forest (what SHAP explains)
  engine2_calibrator.pkl  LogisticRegression on logit(raw P) — Platt scaling,
                          fitted on out-of-fold predictions at the natural
                          (un-SMOTEd) class balance of the development set
  engine2_feature_names.npy, engine2_metadata.json, engine2_results.csv

Artefacts go to `models v4/` (provenance, with regenerated plots) and to
backend/models/ (serving). The 15% held-out test split is scored once, after
fitting, and never used for any choice.

    cd backend && .venv/Scripts/python scripts/train_engine2_random_forest.py
"""
import json
import pickle
import shutil
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine2_model_comparison as cmp  # noqa: E402

REPO_ROOT = cmp.REPO_ROOT
SERVING_DIR = cmp.DEPLOYED_MODELS_DIR
PROVENANCE_DIR = REPO_ROOT / "models v4"
COMPARISON_DIR = cmp.DEFAULT_OUT_DIR
SHAP_WATERFALL_TOP_N = 10


def fit_deployment_artifacts(X_dev: pd.DataFrame, y_dev: pd.Series):
    """Return (raw Random Forest, Platt calibrator, OOF raw probabilities)."""
    oof_raw = cmp.oof_raw_probs(X_dev, y_dev)
    calibrator = cmp.fit_sigmoid(oof_raw, y_dev)
    forest = cmp.rf_pipeline().fit(X_dev, y_dev).named_steps["rf"]
    return forest, calibrator, oof_raw


def score_test_split(forest, calibrator, X_test: pd.DataFrame, y_test: pd.Series) -> tuple[dict, np.ndarray, np.ndarray]:
    raw = forest.predict_proba(X_test)[:, 1]
    calibrated = cmp.apply_sigmoid(calibrator, raw)
    y = y_test.to_numpy()
    return {"raw": cmp.score(y, raw), "calibrated": cmp.score(y, calibrated)}, raw, calibrated


def plot_evaluation(y_test, calibrated, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns
    from sklearn.metrics import confusion_matrix, roc_auc_score, roc_curve

    y = np.asarray(y_test)
    predicted = (calibrated >= cmp.DECISION_THRESHOLD).astype(int)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    sns.heatmap(confusion_matrix(y, predicted), annot=True, fmt="d", cmap="Blues", ax=axes[0],
                xticklabels=["Low", "High"], yticklabels=["Low", "High"])
    axes[0].set(title="Random Forest (calibrated) - Confusion Matrix (held-out test)",
                ylabel="Actual", xlabel="Predicted")
    fpr, tpr, _ = roc_curve(y, calibrated)
    axes[1].plot(fpr, tpr, linewidth=2, label=f"AUC={roc_auc_score(y, calibrated):.3f}")
    axes[1].plot([0, 1], [0, 1], "k--", alpha=0.4)
    axes[1].set(title="Random Forest (calibrated) - ROC Curve", xlabel="False Positive Rate",
                ylabel="True Positive Rate")
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_comparison(path: Path) -> None:
    """Bar chart of the repeated-CV results (docs/engine2_model_comparison/)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    summary = pd.read_csv(COMPARISON_DIR / "cv_summary.csv", index_col=0)
    metrics = ["F1", "ROC_AUC", "Recall", "Brier", "ECE"]
    models = [m for m in summary.index if m != cmp.ORACLE]
    width = 0.8 / len(models)
    fig, ax = plt.subplots(figsize=(11, 5))
    for i, model in enumerate(models):
        means = [summary.loc[model, f"{m}_mean"] for m in metrics]
        errs = [summary.loc[model, f"{m}_std"] for m in metrics]
        ax.bar(np.arange(len(metrics)) + i * width, means, width, yerr=errs, capsize=3,
               label=model, alpha=0.85)
    ax.set_xticks(np.arange(len(metrics)) + width * (len(models) - 1) / 2)
    ax.set_xticklabels(["F1", "ROC-AUC", "Recall", "Brier (lower=better)", "ECE (lower=better)"])
    ax.set_title("Engine 2 - 5x5 repeated stratified CV (mean ± std); hand-set, untuned hyperparameters",
                 fontweight="bold", fontsize=10)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_shap(forest, X_test: pd.DataFrame, calibrated, out_dir: Path) -> None:
    """SHAP importance / beeswarm / waterfall of the deployed forest (class 1)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import shap

    explainer = shap.TreeExplainer(forest)
    values = np.asarray(explainer.shap_values(X_test))[:, :, 1]
    base = float(np.ravel(explainer.expected_value)[1])
    note = "explains the raw forest probability; the served score applies monotone Platt calibration"

    shap.summary_plot(values, X_test, plot_type="bar", show=False)
    plt.title(f"Mean |SHAP| - Random Forest ({note})", fontsize=8)
    plt.tight_layout()
    plt.savefig(out_dir / "shap_importance.png", dpi=150, bbox_inches="tight")
    plt.close()

    shap.summary_plot(values, X_test, show=False)
    plt.title("SHAP summary - Random Forest, class 1 (high risk)", fontsize=9)
    plt.tight_layout()
    plt.savefig(out_dir / "shap_summary.png", dpi=150, bbox_inches="tight")
    plt.close()

    worst = int(np.argmax(calibrated))
    explanation = shap.Explanation(values=values[worst], base_values=base,
                                   data=X_test.iloc[worst].to_numpy(), feature_names=list(X_test.columns))
    shap.plots.waterfall(explanation, max_display=SHAP_WATERFALL_TOP_N, show=False)
    plt.title(f"Highest-risk test profile (calibrated P={calibrated[worst]:.3f})", fontsize=9)
    plt.savefig(out_dir / "shap_waterfall_highrisk.png", dpi=150, bbox_inches="tight")
    plt.close()


def build_metadata(calibrator, test_scores: dict) -> dict:
    cv = pd.read_csv(COMPARISON_DIR / "cv_summary.csv", index_col=0)
    calib_cv = pd.read_csv(COMPARISON_DIR / "calibration_summary.csv", index_col=0)
    keep = ["F1", "ROC_AUC", "Recall", "Precision", "Accuracy", "Brier", "LogLoss", "ECE"]
    return {
        "engine": 2,
        "task": "bnpl_risk_classification",
        "winner": "Random Forest",
        "selection_criterion": "repeated_stratified_cv_ROC_AUC_and_Brier_with_corrected_resampled_ttest",
        "hyperparameters": "hand-set, untuned (identical treatment for Random Forest, XGBoost and LightGBM)",
        "features": cmp.FEATURES,
        "calibration": {
            "method": "sigmoid (Platt scaling on log-odds of raw forest probability)",
            "fitted_on": "5-fold out-of-fold predictions of the development set, natural class balance",
            "chosen_over": "isotonic (no significant gain, adds plateaus/ties) and none",
            "platt_coef": float(calibrator.coef_[0][0]),
            "platt_intercept": float(calibrator.intercept_[0]),
        },
        "cv_results_5x5": {m: {k: round(float(cv.loc[m, f"{k}_mean"]), 4) for k in keep} for m in cv.index},
        "calibration_cv_results_5x5": {
            m: {k: round(float(calib_cv.loc[m, f"{k}_mean"]), 4) for k in keep} for m in calib_cv.index
        },
        "held_out_test": {k: {m: round(float(v), 4) for m, v in s.items()} for k, s in test_scores.items()},
        "data": {
            "source": "synthetic_bnpl_scenarios_v3_continuous_labels (N=2000)",
            "split": "85% development (CV + fitting) / 15% held-out test, stratified, seed 42",
            "smote": "applied on training folds / final training set only",
        },
        "library_versions": {"scikit-learn": sklearn.__version__, "numpy": np.__version__},
        "generated_at": datetime.now().isoformat(),
    }


def export_artifacts(forest, calibrator, metadata: dict, results: pd.DataFrame) -> None:
    for target in (PROVENANCE_DIR, SERVING_DIR):
        target.mkdir(parents=True, exist_ok=True)
        for filename, payload in (("engine2_winner.pkl", forest), ("engine2_calibrator.pkl", calibrator)):
            with open(target / filename, "wb") as f:
                pickle.dump(payload, f)
        np.save(target / "engine2_feature_names.npy", np.array(cmp.FEATURES))
        (target / "engine2_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf8")
        results.to_csv(target / "engine2_results.csv")


def main() -> None:
    df, _ = cmp.load_dataset()
    X, y = df[cmp.FEATURES], df[cmp.TARGET]
    idx_dev, idx_test = train_test_split(
        np.arange(len(df)), test_size=cmp.TEST_SIZE, random_state=cmp.SEED, stratify=y
    )
    X_dev, y_dev = X.iloc[idx_dev].reset_index(drop=True), y.iloc[idx_dev].reset_index(drop=True)
    X_test, y_test = X.iloc[idx_test], y.iloc[idx_test]

    forest, calibrator, _ = fit_deployment_artifacts(X_dev, y_dev)
    test_scores, raw, calibrated = score_test_split(forest, calibrator, X_test, y_test)

    metadata = build_metadata(calibrator, test_scores)
    results = pd.DataFrame(test_scores).T
    export_artifacts(forest, calibrator, metadata, results)

    PROVENANCE_DIR.mkdir(exist_ok=True)
    plot_evaluation(y_test, calibrated, PROVENANCE_DIR / "random_forest_eval.png")
    plot_comparison(PROVENANCE_DIR / "engine2_comparison.png")
    plot_shap(forest, X_test, calibrated, PROVENANCE_DIR)
    for name in ("calibration_reliability.png", "reliability.png"):
        source = COMPARISON_DIR / name
        if source.exists():
            shutil.copy(source, PROVENANCE_DIR / name)

    print(f"Platt: coef={calibrator.coef_[0][0]:.4f} intercept={calibrator.intercept_[0]:.4f}")
    print("Held-out test (one-shot, informational):")
    print(pd.DataFrame(test_scores).T.round(4).to_string())
    print(f"Artefacts: {PROVENANCE_DIR} and {SERVING_DIR}")


if __name__ == "__main__":
    main()
