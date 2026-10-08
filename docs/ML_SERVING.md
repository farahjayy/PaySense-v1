# PaySense — ML Serving Design

The trained artefacts live in `models v2/` (repo root) and are copied to `backend/models/` in Phase 0. **`models v2/` itself is frozen** — it's the evaluation provenance behind the already-graded Interim Report/Proposal Defence and must never be edited. The training notebooks are *not* frozen the same way: `paysense_engine2_classification.ipynb` was retrained on 2026-09-16 (see `docs/KNOWN_LIMITATIONS.md`) with its output artefacts landing in a new **`models v3/`** folder, leaving `models v2/` untouched. Future retrains should follow the same pattern — new artefacts get a new `models vN/` folder (`models v4/` = the current Random Forest + calibrator, regenerated SHAP/comparison plots, produced by `backend/scripts/train_engine2_random_forest.py`); `backend/models/` (the serving copy) gets updated to point at whichever is current.

| Artefact | Role at serve time |
|---|---|
| `engine1_winner.pkl` | NOT loaded. ARIMA won the evaluation (RMSE 7,300.30 on Kaggle 2024 hold-out); serving refits on user data instead (§1). Keep as provenance. |
| `engine2_winner.pkl` | **Loaded once at startup**, via plain `pickle.load` — the raw **Random Forest** (deployed 2026-09-25 from `models v4/`; 5×5 repeated-CV F1 0.826, ROC-AUC 0.868, Brier 0.146 on the v3 continuous-label dataset). This is the model SHAP explains. All three candidates (Random Forest, XGBoost, LightGBM) used hand-set, untuned hyperparameters, so the model comparison should be read as a like-for-like comparison of defaults, not of tuned optima. |
| `engine2_calibrator.pkl` | **Loaded once at startup.** Platt scaling (a `LogisticRegression` on the log-odds of the forest's raw P(risk), fitted on out-of-fold predictions at the natural class balance). `Engine2.calibrate()` applies it, and `risk.predict_risk` returns the *calibrated* probability behind the 0–100 score. It is strictly increasing, so SHAP factor ranking (computed on the raw forest output) is unaffected. Sigmoid was chosen over isotonic and no calibration by nested CV (see `docs/KNOWN_LIMITATIONS.md`). |
| `engine2_feature_names.npy` | Loaded at startup — the authoritative feature order. |
| `engine1_metadata.json`, `engine2_metadata.json` | Metrics + winner provenance. **No library versions or ARIMA order recorded** — do not try to read them from here. `engine2_metadata.json`'s `data.source` tag records which label-generation version produced the dataset (e.g. `synthetic_bnpl_scenarios_v3_continuous_labels`). |

**Startup smoke test** (`backend/scripts/smoke_test_models.py`, also run in Phase 2 CI): load both pkls + npy, assert 11 feature names match §2 order, run one dummy prediction (raw + calibrated), and check SHAP wiring (shape `(1, 11, 2)`; `expected_value[1] + Σ shap` reproduces the raw probability). Unpickle failure ⇒ the pinned `scikit-learn` version needs adjusting; still failing ⇒ stop and report. `xgboost`/`lightgbm` stay installed only for the comparison scripts.

## 1. Engine 1 — Cash flow forecasting (`services/forecasting.py`)

1. **Series construction:** aggregate `transactions` into monthly net cashflow (income − expenses), a `pd.Series` indexed by month start. Months with no data inside the user's active range = 0, not NaN.
2. **Fit:** mirrors the validated pattern in `paysense_engine1_forecasting.ipynb` cell 34:
   ```python
   from pmdarima import auto_arima
   model = auto_arima(series, seasonal=False, stepwise=True,
                      suppress_warnings=True, error_action="ignore")
   net_forecast = model.predict(n_periods=3)
   ```
   `seasonal=False` is deliberate — the user series has <12 months, insufficient for m=12 seasonality (same reason the notebook's personal demo disabled it). Fit takes milliseconds at this size; refit per request, no caching needed for the demo.
3. **Income/expense split for the chart:** forecast net; split into income/expense components using each one's own 3-month trailing average scaled so their difference equals the forecast net (keeps the bar chart honest without fitting three models).
4. **Weekly balance curve:** start at `app_state.current_balance`; for each of the next ~13 weeks add `(that month's forecast net)/weeks_in_month`, subtract every unpaid instalment of **active BNPL plans** on the week containing its due date. Collect points where balance < `LOW_BALANCE_THRESHOLD_RM` (50).
5. **Fallback:** if the series has < 3 non-empty months, skip ARIMA and use the trailing 3-month moving average (or overall mean if fewer); tag `method: "fallback_ma"`. Never 500 on sparse data.

## 2. Engine 2 — Risk classification (`services/risk.py` + `services/features.py`)

### Feature vector — exact order from `engine2_feature_names.npy`:

| # | Feature | Source at serve time |
|---|---|---|
| 1 | `age` | `app_state.profile.age` (default 22) |
| 2 | `employment_status` | `app_state.profile.employment_status` — **encoding: 0=student, 1=employed, 2=self-employed, 3=unemployed** (verified against notebook cell 7; must never change) |
| 3 | `monthly_income` | mean monthly income, last 3 full months of transactions |
| 4 | `monthly_expenses` | mean monthly expenses, last 3 full months |
| 5 | `num_bnpl_plans` | count of active plans **+ 1 for the proposed purchase** |
| 6 | `bnpl_outstanding` | sum of unpaid instalment amounts across active plans **+ total payable of the proposed purchase** |
| 7 | `missed_payments` | count of overdue (unpaid, past-due) instalments, last 6 months |
| 8 | `forecasted_cash_flow` | **Engine 1 linkage:** mean of the 3 forecast months' net cashflow, computed on the curve that already includes the proposed instalments |
| 9 | `income_expense_ratio` | monthly_income / monthly_expenses (guard div-by-zero → cap ratio features at sensible bounds when denominator is 0) |
| 10 | `bnpl_income_ratio` | **total BNPL debt** (`bnpl_outstanding`, incl. the proposed purchase, excl. any part paid at checkout) / monthly_income — the definition the model was trained on (changed 2026-09-27; it was served as monthly instalment burden / income, which understated it) |
| 11 | `savings_rate` | (monthly_income − monthly_expenses) / monthly_income |

Build as a single-row DataFrame with those exact column names; assert order equals the npy at startup.

### Scoring
```
p = model.predict_proba(X)[0, 1]        # P(high risk)
score = round((1 - p) * 100)            # health score
label: safe (70–100) · caution (40–69) · at_risk (0–39)
```

## 3. SHAP explanation layer

`shap.TreeExplainer(model)` created once at startup. Per check: compute SHAP values for the single row, take the top 3 features with **positive** contribution toward class 1 (risk), map through templates:

| Feature | Template (fill with actual values) |
|---|---|
| num_bnpl_plans | "You already have {n} active BNPL plans" |
| bnpl_income_ratio | "Your total BNPL debt is {pct}% of your monthly income" |
| forecasted_cash_flow | "Your forecasted monthly cash flow is {sign}RM {v}" |
| missed_payments | "You've missed {n} payments in the last 6 months" |
| savings_rate | "You're currently saving {pct}% of your income" |
| monthly_expenses / income_expense_ratio | "Your spending is {pct}% of your income" |
| bnpl_outstanding | "You'd owe RM {v} across all BNPL plans" |
| age / employment_status | "Your profile (student, {age}) matches a higher-risk group" |

Additionally, if the with-purchase curve dips below RM50, always append: "Your projected balance drops below RM{threshold} on {date}" (from Engine 1, not SHAP — it's the most concrete fact the user gets).

## 4. Recommendation & dashboard health score

- **Recommendation:** `safe` → "Safe to proceed — your projected balance stays healthy." · `caution` → "Consider delaying — your balance dips to RM{min} around {date}." (suggest delaying past the dip week) · `at_risk` → "Avoid this purchase — projected deficit of RM{v} in {month}."
- **Dashboard speedometer:** runs the same Engine 2 pipeline **without any proposed purchase** (current commitments only). Compute on `GET /api/dashboard`. If ML fails, degrade to a rule-based score (income/expense ratio + BNPL burden) and flag `"health_source": "rules"` — the dashboard must never be blank.
