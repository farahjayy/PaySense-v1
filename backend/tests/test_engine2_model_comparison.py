"""Unit tests for the Engine 2 model-comparison script's pure helpers."""
import numpy as np
import pytest
from scipy import stats

from scripts import engine2_model_comparison as cmp


def test_ece_is_zero_for_perfectly_calibrated_bins():
    y = np.array([0, 0, 0, 1, 1, 1, 1, 1, 1, 1])
    p = np.array([0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0])

    assert cmp.expected_calibration_error(y, p) == pytest.approx(0.0)


def test_ece_measures_overconfidence():
    y = np.array([0, 1, 0, 1])  # 50% observed
    p = np.array([0.9, 0.9, 0.9, 0.9])  # claims 90%

    assert cmp.expected_calibration_error(y, p) == pytest.approx(0.4)


def test_ece_handles_probability_of_exactly_one():
    assert cmp.expected_calibration_error(np.array([1, 1]), np.array([1.0, 1.0])) == pytest.approx(0.0)


def test_corrected_ttest_is_more_conservative_than_plain_paired_ttest():
    diffs = np.array([0.02, 0.01, 0.03, 0.015, 0.025, 0.02, 0.01, 0.03])

    _, corrected_p = cmp.corrected_resampled_ttest(diffs, n_train=100, n_test=25)
    plain_p = stats.ttest_1samp(diffs, 0.0).pvalue

    assert corrected_p > plain_p


def test_corrected_ttest_matches_nadeau_bengio_formula():
    diffs = np.array([0.01, -0.02, 0.03, 0.0, 0.015])
    expected_t = diffs.mean() / np.sqrt((1 / 5 + 25 / 100) * diffs.var(ddof=1))

    t_stat, p_value = cmp.corrected_resampled_ttest(diffs, n_train=100, n_test=25)

    assert t_stat == pytest.approx(expected_t)
    assert p_value == pytest.approx(2 * stats.t.sf(abs(expected_t), df=4))


def test_corrected_ttest_identical_models_give_p_of_one():
    t_stat, p_value = cmp.corrected_resampled_ttest(np.zeros(10), n_train=100, n_test=25)

    assert (t_stat, p_value) == (0.0, 1.0)


def test_score_returns_every_metric_and_perfect_predictions_score_one():
    y = np.array([0, 0, 1, 1])
    result = cmp.score(y, np.array([0.1, 0.2, 0.8, 0.9]))

    assert set(result) == set(cmp.METRICS)
    assert result["F1"] == 1.0 and result["ROC_AUC"] == 1.0


def test_dataset_loader_reuses_notebook_label_logic():
    df, true_prob = cmp.load_dataset()

    assert len(df) == len(true_prob) == 2000
    assert list(df[cmp.FEATURES].columns) == cmp.FEATURES
    assert ((true_prob >= 0) & (true_prob <= 1)).all()
