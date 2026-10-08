"""Engine 2 model comparison — repeated stratified k-fold CV + calibration.

Motivation (docs/KNOWN_LIMITATIONS.md): the notebook picked the winner from a
single ~300-row test split, where RF / XGBoost / LightGBM differ by ~0.003 F1
(about one row). This script re-compares them properly:

  * repeated stratified k-fold on the 85% development set (the 15% test set
    is left untouched until one final, informational check);
  * SMOTE fitted on each training fold only (as in the notebook);
  * per-fold F1 / ROC-AUC / recall / precision / accuracy plus calibration
    (Brier score, log loss, expected calibration error);
  * Nadeau-Bengio corrected resampled t-test for pairwise differences;
  * an "oracle" row scored with the TRUE generating probability, i.e. the
    ceiling any model can reach on this synthetic label. Since the label is a
    Bernoulli draw from that probability, the gap to the oracle is what is
    actually learnable.

It reuses the dataset generator in paysense_engine2_classification.ipynb (so
the label logic cannot drift) and NEVER writes to backend/models/: the
deployed model is untouched. Hyperparameters mirror the notebook, except
LightGBM runs without early stopping (there is no fixed validation set per CV
fold), so its numbers are not identical to the notebook's.

    cd backend && .venv/Scripts/python scripts/engine2_model_comparison.py
"""
import argparse
import contextlib
import io
import json
import warnings
from itertools import combinations
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import xgboost as xgb
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
from scipy import stats
from sklearn.ensemble import RandomForestClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import RepeatedStratifiedKFold, StratifiedKFold, train_test_split

REPO_ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK = REPO_ROOT / "paysense_engine2_classification.ipynb"
DEPLOYED_MODELS_DIR = REPO_ROOT / "backend" / "models"
DEFAULT_OUT_DIR = REPO_ROOT / "docs" / "engine2_model_comparison"

SEED = 42
TEST_SIZE = 0.15
DECISION_THRESHOLD = 0.5
CALIBRATION_BINS = 10
LABEL_CELL_MARKER = "TARGET: BNPL RISK"
FEATURES = [
    "age", "employment_status", "monthly_income", "monthly_expenses",
    "num_bnpl_plans", "bnpl_outstanding", "missed_payments",
    "forecasted_cash_flow", "income_expense_ratio", "bnpl_income_ratio",
    "savings_rate",
]
TARGET = "bnpl_risk"
ORACLE = "Oracle (true probability)"
METRICS = ["F1", "ROC_AUC", "Recall", "Precision", "Accuracy", "Brier", "LogLoss", "ECE"]
TESTED_METRICS = ["F1", "ROC_AUC", "Brier"]
CALIBRATION_TESTED_METRICS = ["Brier", "LogLoss", "ECE", "F1", "ROC_AUC"]
CALIBRATION_METHODS = ("none", "sigmoid", "isotonic")
INNER_FOLDS = 5
PROB_EPS = 1e-6


def load_dataset() -> tuple[pd.DataFrame, np.ndarray]:
    """Run the notebook's data-generation cell; return (df, true P(risk))."""
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf8"))
    source = next(
        "".join(cell["source"])
        for cell in notebook["cells"]
        if cell["cell_type"] == "code" and LABEL_CELL_MARKER in "".join(cell["source"])
    )
    namespace = {"np": np, "pd": pd, "SEED": SEED}
    with contextlib.redirect_stdout(io.StringIO()):
        exec(source, namespace)  # noqa: S102 - our own notebook cell, not user input
    return namespace["df"], np.asarray(namespace["risk_prob"])


def build_models() -> dict:
    """Fresh, unfitted candidates with the notebook's hyperparameters."""
    return {
        "Random Forest": RandomForestClassifier(
            n_estimators=200, max_depth=10, min_samples_split=5,
            min_samples_leaf=2, class_weight="balanced",
            random_state=SEED, n_jobs=-1,
        ),
        "XGBoost": xgb.XGBClassifier(
            n_estimators=300, max_depth=6, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8,
            eval_metric="logloss", random_state=SEED, n_jobs=-1, verbosity=0,
        ),
        "LightGBM": lgb.LGBMClassifier(
            n_estimators=300, max_depth=6, learning_rate=0.05, num_leaves=31,
            subsample=0.8, colsample_bytree=0.8, class_weight="balanced",
            random_state=SEED, n_jobs=-1, verbose=-1,
        ),
    }


def expected_calibration_error(y_true, y_prob, n_bins: int = CALIBRATION_BINS) -> float:
    """Weighted mean |observed rate - mean predicted prob| over equal-width bins."""
    y_true, y_prob = np.asarray(y_true), np.asarray(y_prob)
    bin_ids = np.minimum((y_prob * n_bins).astype(int), n_bins - 1)
    error = 0.0
    for b in range(n_bins):
        mask = bin_ids == b
        if mask.any():
            error += mask.mean() * abs(y_true[mask].mean() - y_prob[mask].mean())
    return float(error)


def score(y_true, y_prob) -> dict:
    """All comparison metrics for one set of held-out predictions."""
    y_pred = (y_prob >= DECISION_THRESHOLD).astype(int)
    clipped = np.clip(y_prob, 1e-6, 1 - 1e-6)
    return {
        "F1": f1_score(y_true, y_pred, zero_division=0),
        "ROC_AUC": roc_auc_score(y_true, y_prob),
        "Recall": recall_score(y_true, y_pred, zero_division=0),
        "Precision": precision_score(y_true, y_pred, zero_division=0),
        "Accuracy": accuracy_score(y_true, y_pred),
        "Brier": brier_score_loss(y_true, y_prob),
        "LogLoss": log_loss(y_true, clipped),
        "ECE": expected_calibration_error(y_true, y_prob),
    }


def corrected_resampled_ttest(diffs, n_train: int, n_test: int) -> tuple[float, float]:
    """Nadeau-Bengio corrected t-test on per-fold paired differences.

    Plain paired t-tests over CV folds are too optimistic because the training
    sets overlap; the correction inflates the variance by n_test/n_train.
    Returns (t statistic, two-sided p-value).
    """
    diffs = np.asarray(diffs, dtype=float)
    n = len(diffs)
    variance = diffs.var(ddof=1)
    if variance == 0:
        return (0.0, 1.0) if diffs.mean() == 0 else (float("inf"), 0.0)
    t_stat = diffs.mean() / np.sqrt((1 / n + n_test / n_train) * variance)
    return float(t_stat), float(2 * stats.t.sf(abs(t_stat), df=n - 1))


def run_cv(X: pd.DataFrame, y: pd.Series, oracle_prob: np.ndarray, folds: int, repeats: int):
    """Return (per-fold metrics DataFrame, pooled out-of-fold predictions)."""
    splitter = RepeatedStratifiedKFold(n_splits=folds, n_repeats=repeats, random_state=SEED)
    rows, pooled = [], {name: ([], []) for name in [*build_models(), ORACLE]}
    n_train = n_test = 0

    for fold_idx, (train_idx, test_idx) in enumerate(splitter.split(X, y)):
        n_train, n_test = len(train_idx), len(test_idx)
        X_sm, y_sm = SMOTE(random_state=SEED, k_neighbors=5).fit_resample(
            X.iloc[train_idx], y.iloc[train_idx]
        )
        y_test = y.iloc[test_idx].to_numpy()
        predictions = {ORACLE: oracle_prob[test_idx]}
        for name, model in build_models().items():
            model.fit(X_sm, y_sm)
            predictions[name] = model.predict_proba(X.iloc[test_idx])[:, 1]

        for name, prob in predictions.items():
            rows.append({"fold": fold_idx, "model": name, **score(y_test, prob)})
            pooled[name][0].append(y_test)
            pooled[name][1].append(prob)
        print(f"  fold {fold_idx + 1}/{folds * repeats} done", flush=True)

    pooled = {k: (np.concatenate(v[0]), np.concatenate(v[1])) for k, v in pooled.items()}
    return pd.DataFrame(rows), pooled, n_train, n_test


def summarise(fold_df: pd.DataFrame) -> pd.DataFrame:
    grouped = fold_df.groupby("model")[METRICS]
    summary = grouped.mean().add_suffix("_mean").join(grouped.std().add_suffix("_std"))
    return summary.sort_values("F1_mean", ascending=False)


def pairwise_tests(
    fold_df: pd.DataFrame, n_train: int, n_test: int, metrics: list[str] = TESTED_METRICS
) -> pd.DataFrame:
    candidates = [m for m in fold_df["model"].unique() if m != ORACLE]
    rows = []
    for a, b in combinations(candidates, 2):
        for metric in metrics:
            va = fold_df[fold_df.model == a].sort_values("fold")[metric].to_numpy()
            vb = fold_df[fold_df.model == b].sort_values("fold")[metric].to_numpy()
            t_stat, p_value = corrected_resampled_ttest(va - vb, n_train, n_test)
            rows.append({
                "A": a, "B": b, "metric": metric,
                "mean_diff_A_minus_B": float((va - vb).mean()),
                "t": t_stat, "p_value": p_value,
                "significant_at_0.05": p_value < 0.05,
            })
    return pd.DataFrame(rows)


def rf_pipeline() -> ImbPipeline:
    """SMOTE + Random Forest, as deployed: SMOTE only ever sees training rows."""
    return ImbPipeline([
        ("smote", SMOTE(random_state=SEED, k_neighbors=5)),
        ("rf", build_models()["Random Forest"]),
    ])


def oof_raw_probs(X: pd.DataFrame, y: pd.Series, folds: int = INNER_FOLDS) -> np.ndarray:
    """Out-of-fold raw RF P(risk) on the natural (un-SMOTEd) class balance.

    Calibrators must be fitted on predictions the model did not train on, and
    on the real class balance: the RF itself trains on SMOTE-balanced data, so
    its raw probabilities are biased toward the minority (low-risk) class.
    """
    oof = np.zeros(len(y))
    for train_idx, test_idx in StratifiedKFold(folds, shuffle=True, random_state=SEED).split(X, y):
        model = rf_pipeline().fit(X.iloc[train_idx], y.iloc[train_idx])
        oof[test_idx] = model.predict_proba(X.iloc[test_idx])[:, 1]
    return oof


def _logit(prob) -> np.ndarray:
    clipped = np.clip(np.asarray(prob, dtype=float), PROB_EPS, 1 - PROB_EPS)
    return np.log(clipped / (1 - clipped)).reshape(-1, 1)


def fit_isotonic(raw_prob, y) -> IsotonicRegression:
    return IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip").fit(raw_prob, y)


def fit_sigmoid(raw_prob, y) -> LogisticRegression:
    """Platt scaling: a near-unpenalised logistic fit on the log-odds of the raw probability."""
    return LogisticRegression(C=1e6).fit(_logit(raw_prob), y)


def apply_sigmoid(platt: LogisticRegression, raw_prob) -> np.ndarray:
    return platt.predict_proba(_logit(raw_prob))[:, 1]


def fit_calibrator(method: str, raw_prob, y):
    """Return a callable mapping raw RF probabilities to calibrated ones."""
    if method == "none":
        return lambda p: np.asarray(p, dtype=float)
    if method == "isotonic":
        return fit_isotonic(raw_prob, y).predict
    if method == "sigmoid":
        platt = fit_sigmoid(raw_prob, y)
        return lambda p: apply_sigmoid(platt, p)
    raise ValueError(f"unknown calibration method: {method}")


def run_calibration_cv(X: pd.DataFrame, y: pd.Series, folds: int, repeats: int):
    """Nested CV: calibrators are fitted on inner out-of-fold predictions of
    each outer training fold, then scored on the untouched outer test fold."""
    splitter = RepeatedStratifiedKFold(n_splits=folds, n_repeats=repeats, random_state=SEED)
    rows, pooled = [], {m: ([], []) for m in CALIBRATION_METHODS}
    n_train = n_test = 0

    for fold_idx, (train_idx, test_idx) in enumerate(splitter.split(X, y)):
        n_train, n_test = len(train_idx), len(test_idx)
        X_tr, y_tr = X.iloc[train_idx], y.iloc[train_idx]
        raw_train_oof = oof_raw_probs(X_tr, y_tr)
        raw_test = rf_pipeline().fit(X_tr, y_tr).predict_proba(X.iloc[test_idx])[:, 1]
        y_test = y.iloc[test_idx].to_numpy()

        for method in CALIBRATION_METHODS:
            prob = fit_calibrator(method, raw_train_oof, y_tr)(raw_test)
            rows.append({"fold": fold_idx, "model": method, **score(y_test, prob)})
            pooled[method][0].append(y_test)
            pooled[method][1].append(prob)
        print(f"  calibration fold {fold_idx + 1}/{folds * repeats} done", flush=True)

    pooled = {k: (np.concatenate(v[0]), np.concatenate(v[1])) for k, v in pooled.items()}
    return pd.DataFrame(rows), pooled, n_train, n_test


def final_test_check(X_dev, y_dev, X_test, y_test) -> pd.DataFrame:
    """One-shot evaluation on the untouched test split (informational only)."""
    X_sm, y_sm = SMOTE(random_state=SEED, k_neighbors=5).fit_resample(X_dev, y_dev)
    rows = []
    for name, model in build_models().items():
        model.fit(X_sm, y_sm)
        rows.append({"model": name, **score(y_test.to_numpy(), model.predict_proba(X_test)[:, 1])})
    return pd.DataFrame(rows).set_index("model")


def plot_reliability(pooled: dict, path: Path, title: str = "Engine 2 reliability (pooled out-of-fold)") -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([0, 1], [0, 1], "k--", alpha=0.4, label="Perfectly calibrated")
    edges = np.linspace(0, 1, CALIBRATION_BINS + 1)
    for name, (y_true, y_prob) in pooled.items():
        bin_ids = np.minimum(np.digitize(y_prob, edges[1:-1]), CALIBRATION_BINS - 1)
        xs = [y_prob[bin_ids == b].mean() for b in range(CALIBRATION_BINS) if (bin_ids == b).any()]
        ys = [y_true[bin_ids == b].mean() for b in range(CALIBRATION_BINS) if (bin_ids == b).any()]
        ax.plot(xs, ys, marker="o", linewidth=1.5, label=name)
    ax.set_xlabel("Mean predicted P(risk)")
    ax.set_ylabel("Observed high-risk rate")
    ax.set_title(title)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _fmt_summary(summary: pd.DataFrame) -> str:
    lines = []
    for model, row in summary.iterrows():
        cells = " | ".join(f"{row[f'{m}_mean']:.4f} ± {row[f'{m}_std']:.4f}" for m in METRICS)
        lines.append(f"| {model} | {cells} |")
    header = "| Model | " + " | ".join(METRICS) + " |\n|" + "---|" * (len(METRICS) + 1)
    return header + "\n" + "\n".join(lines)


def run_calibration_report(X_dev, y_dev, args, out_dir: Path) -> None:
    print(f"Running {args.repeats}x{args.folds}-fold nested calibration CV (Random Forest)...")
    fold_df, pooled, n_train, n_test = run_calibration_cv(X_dev, y_dev, args.folds, args.repeats)
    summary = summarise(fold_df)
    tests = pairwise_tests(fold_df, n_train, n_test, CALIBRATION_TESTED_METRICS)
    fold_df.to_csv(out_dir / "calibration_fold_metrics.csv", index=False)
    summary.to_csv(out_dir / "calibration_summary.csv")
    tests.to_csv(out_dir / "calibration_pairwise_tests.csv", index=False)
    plot_reliability(pooled, out_dir / "calibration_reliability.png",
                     "Random Forest reliability by calibration method (nested CV)")
    print("\n## Calibration methods (mean ± std over folds)\n")
    print(_fmt_summary(summary))
    print("\n## Pairwise corrected resampled t-tests (A - B)\n")
    print(tests.round(4).to_string(index=False))
    print(f"\nOutputs written to {out_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument(
        "--calibration", action="store_true",
        help="Compare none/sigmoid/isotonic calibration of the Random Forest (nested CV) instead of the model comparison.",
    )
    args = parser.parse_args()

    out_dir = args.out_dir.resolve()
    if DEPLOYED_MODELS_DIR.resolve() in (out_dir, *out_dir.parents):
        raise SystemExit("Refusing to write into backend/models/ - the deployed model must not change.")
    out_dir.mkdir(parents=True, exist_ok=True)
    warnings.filterwarnings("ignore")

    df, true_prob = load_dataset()
    X, y = df[FEATURES], df[TARGET]
    idx_dev, idx_test = train_test_split(
        np.arange(len(df)), test_size=TEST_SIZE, random_state=SEED, stratify=y
    )
    X_dev, y_dev = X.iloc[idx_dev].reset_index(drop=True), y.iloc[idx_dev].reset_index(drop=True)
    print(f"Dataset {len(df)} rows | dev {len(idx_dev)} | held-out test {len(idx_test)} "
          f"| high-risk share {y.mean():.3f}")
    if args.calibration:
        run_calibration_report(X_dev, y_dev, args, out_dir)
        return
    print(f"Running {args.repeats}x{args.folds}-fold CV on the dev set...")

    fold_df, pooled, n_train, n_test = run_cv(
        X_dev, y_dev, true_prob[idx_dev], args.folds, args.repeats
    )
    summary = summarise(fold_df)
    tests = pairwise_tests(fold_df, n_train, n_test)
    test_check = final_test_check(X_dev, y_dev, X.iloc[idx_test], y.iloc[idx_test])

    fold_df.to_csv(out_dir / "cv_fold_metrics.csv", index=False)
    summary.to_csv(out_dir / "cv_summary.csv")
    tests.to_csv(out_dir / "pairwise_tests.csv", index=False)
    test_check.to_csv(out_dir / "final_test_check.csv")
    plot_reliability(pooled, out_dir / "reliability.png")

    print("\n## CV summary (mean ± std over folds)\n")
    print(_fmt_summary(summary))
    print("\n## Pairwise corrected resampled t-tests (A - B)\n")
    print(tests.round(4).to_string(index=False))
    print("\n## Final held-out test check (informational, not used for selection)\n")
    print(test_check.round(4).to_string())
    print(f"\nOutputs written to {out_dir}")


if __name__ == "__main__":
    main()
