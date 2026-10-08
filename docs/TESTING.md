# PaySense — Testing Strategy

Pragmatic FYP-demo scope: unit tests on the logic the grade depends on (ML pipeline correctness, money math), light integration tests on the API, manual checklist for UI. Backend: `pytest` in `backend/tests/`. Run: `cd backend && pytest -q`.

## 1. Must-have unit tests (Phase 2)

### Instalment schedule (`test_schedule.py`)
- Sum of generated instalments == total_payable exactly (rounding absorbed by last instalment) — test RM 899 × 6 @ 0%, RM 429 × 3 @ 5%, awkward cases like RM 100 × 3.
- Due dates are monthly from first_payment_date (incl. month-end edge: 31 Jan + 1 month).
- Provider rules (data in `app/providers.py`): SPayLater and TikTok PayLater first due date one month after the purchase, same day (never the purchase date, nothing prepaid); Atome purchase date with the first payment stored as paid; an explicit first_payment_date overrides; Atome's prepaid part is excluded from bnpl_outstanding.
- Money maths is integer sen: fee is a monthly rate, total = price × (1 + rate/100 × n) rounded half up, instalments rounded down with the leftover sen in the last. Pinned cases: 147.62 × 6 @1.5% → 160.91 (26.81 ×5, 26.86); 147.62 × 3 @0% → 49.20, 49.20, 49.22; 147.62 × 12 @1.5% → 174.19 (14.51 ×11, 14.58).
- Interest 0% → sum == total_price.

### Feature vector (`test_features.py`)
- Order and names exactly match `engine2_feature_names.npy`.
- `employment_status` encoding fixed: 0=student, 1=employed, 2=self-employed, 3=unemployed.
- Proposed purchase increments `num_bnpl_plans` and adds total payable to `bnpl_outstanding`.
- Div-by-zero guards: zero income / zero expenses produce finite, capped ratios.
- `forecasted_cash_flow` reflects the with-purchase forecast (mock Engine 1).

### Scoring & buckets (`test_scoring.py`)
- score = round((1−p)×100); p=0 → 100, p=1 → 0.
- Boundaries: 70 → safe, 69 → caution, 40 → caution, 39 → at_risk.

### Forecasting (`test_forecasting.py`)
- ≥3 months → method "arima"; <3 months → "fallback_ma" (never raises).
- Balance curve starts at current_balance; subtracting a known instalment shows up in the right week.
- Monthly income/expense split difference equals forecast net.

### Plan status (`test_status.py`)
- All paid → completed; unpaid past-due → overdue; else active.

## 2. Integration tests (httpx AsyncClient, hit a test Supabase schema or mock the client)

- Transactions CRUD round-trip + filters.
- `POST /api/bnpl/plans` creates correct number of instalments.
- `POST /api/risk/check` → 200 with all response keys; then `risk/confirm` creates the plan with `risk_score_at_creation`; second confirm → 409.
- CSV import: upload fixture → preview rows → confirm → inserted count matches; malformed file → 422 with code.

## 3. Model smoke test (`scripts/smoke_test_models.py`)

Run at Phase 2 start and before any demo: loads pkl + npy, asserts 11 features, runs one prediction, prints P(risk). This is the canary for environment/version drift.

## 4. Manual UI checklist (Phase 5, before the FYP demo)

- [ ] Demo path: dashboard → add transaction → create plan → risk check → confirm → plan appears with badge
- [ ] Each screen: skeleton, empty state (wipe a table to see), error state (stop the backend and reload)
- [ ] 375px / 768px / 1440px — no horizontal scroll, gauge and charts legible
- [ ] CSV import happy path + PDF failure path message
- [ ] Speedometer label colours match score buckets
- [ ] All currency shows `RM x,xxx.xx`; no `NaN`/`undefined` anywhere
- [ ] Refresh on every route works (no client-only routing traps)

## 5. Fixtures

`backend/scripts/fixtures/`: `sample_statement.csv` (~20 rows, mixed categories, one bad row to exercise `skipped`), plus a tiny transactions JSON used by forecasting tests (6 months, known net values with hand-computed expectations).

## 6. Engine calibration & pipeline-consistency regression tests

Added 2026-09-16 after fixing the Engine 2 label-design issue (see `docs/KNOWN_LIMITATIONS.md`).

### Engine 2 calibration (`test_engine2_calibration.py`)
DB-independent, same `_vector()` builder pattern as `test_features.py`. Pins the *fixed* model's behaviour so a future retrain that reintroduces a binary-threshold-style label fails loudly:
- `missed_payments` 0→1 must move risk by a real, non-negligible amount (the old label gave this zero credit below its `>=2` cliff).
- `bnpl_income_ratio` 0.5→3.0 must move risk substantially (the old label plateaued flat above `0.5`).
- The exact iPhone-16e/RM5000/SPayLater scenario that surfaced the issue must no longer score `"safe"` — pinned against the retrained model's real output.

### Pipeline consistency (`test_pipeline.py`)
Uses the `store` fixture (real ML artefacts, faked repo). Asserts `pipeline.run_risk_check()` and `pipeline.dashboard_health()` each feed the *same* feature-vector object to both `predict_risk` and `top_risk_factors` — otherwise the shown score and the shown "why" factors could silently desync — and that `dashboard_health` never includes a hypothetical purchase (`proposed=None` always).

### Engine 1 live regression (`test_engine1_live.py`)
Distinct from `test_forecasting.py`'s synthetic-fixture unit tests — exercises `pipeline.run_forecast()` against the real seeded Supabase project. Self-skips (`pytest.skip`) if `backend/.env` credentials aren't configured. Checks shape/bounds/finiteness and that the real ~12-month transaction history actually triggers the `auto_arima` refit path (`method == "arima"`), not accuracy.
