"""Engine 1 serving-path regression tests against the REAL seeded Supabase
project (not the synthetic fixtures in test_forecasting.py). Self-skips
without live `.env` credentials. Deliberately does not assert forecast
accuracy or re-run backtesting — see docs/TESTING.md §6."""
import math

import pytest

from app.db import repo
from app.services import forecasting, pipeline

NET_SANITY_CEILING = 20_000  # catches gross unit/extrapolation errors, not an accuracy check


@pytest.fixture()
def live_data():
    try:
        transactions = repo.all_transactions()
        state = repo.get_app_state()
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"live Supabase project not reachable — set backend/.env to run this test ({exc})")
    if not transactions:
        pytest.skip("live Supabase project has no seeded transactions")
    return {"transactions": transactions, "state": state}


def test_live_forecast_shape_and_bounds(live_data):
    result = pipeline.run_forecast()

    assert result["method"] in {"arima", "fallback_ma"}

    monthly = result["monthly"]
    assert len(monthly) == 3
    for m in monthly:
        assert math.isfinite(m["income"])
        assert math.isfinite(m["expenses"])
        assert math.isfinite(m["net"])
        assert abs(m["income"] - m["expenses"] - m["net"]) < 0.02
        assert abs(m["net"]) < NET_SANITY_CEILING

    curve = result["balance_curve"]
    assert len(curve) == 14
    assert curve[0]["balance"] == round(float(live_data["state"]["current_balance"]), 2)
    assert all(math.isfinite(p["balance"]) for p in curve)


def test_live_arima_path_actually_triggers(live_data):
    result = forecasting.forecast_monthly(live_data["transactions"])
    assert result["method"] == "arima", (
        "expected the real ~12-month seeded history to trigger the auto_arima "
        "refit path, not the sparse-data fallback"
    )


def test_live_forecast_matches_dashboard_pipeline(live_data):
    direct = forecasting.forecast_monthly(live_data["transactions"])
    via_pipeline = pipeline.run_forecast()
    assert via_pipeline["method"] == direct["method"]
    assert via_pipeline["_months"] == direct["months"]
