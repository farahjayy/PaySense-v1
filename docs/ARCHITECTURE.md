# PaySense — Architecture

## 1. Three-tier overview

```
┌──────────────────────────────────────────────────────────┐
│  frontend/  Next.js 14+ (App Router, TS) + Tailwind      │
│             + Recharts        → http://localhost:3000    │
└───────────────────────┬──────────────────────────────────┘
                        │ REST (JSON) via typed client frontend/lib/api.ts
┌───────────────────────▼──────────────────────────────────┐
│  backend/   FastAPI (Python 3.11)  → http://localhost:8000│
│   ├─ routers/      transactions, bnpl, forecast, risk,   │
│   │                imports, dashboard, balance           │
│   ├─ services/     forecasting.py (Engine 1)             │
│   │                risk.py (Engine 2 + SHAP)             │
│   │                features.py (feature engineering)     │
│   │                schedule.py (instalment generation)   │
│   ├─ models/       engine artefacts (.pkl, .npy, .json)  │
│   ├─ db/           supabase client, schema.sql           │
│   └─ scripts/      seed.py, smoke_test_models.py         │
└───────────────────────┬──────────────────────────────────┘
                        │ supabase-py (service_role key)
┌───────────────────────▼──────────────────────────────────┐
│  Supabase (PostgreSQL, cloud free tier)                   │
│  transactions · bnpl_plans · bnpl_installments ·          │
│  risk_checks · app_state                                  │
└──────────────────────────────────────────────────────────┘
```

- The frontend never talks to Supabase directly — all data flows through FastAPI. This keeps ML and data logic in one place and makes the eventual Render deployment trivial.
- Single-user: no auth middleware, no user scoping anywhere.
- CORS: allow `http://localhost:3000` in FastAPI.

## 2. Sequential AI pipeline (core technical novelty)

The two engines run **in sequence** — Engine 1's forecast is Engine 2's evaluation context. The question is not "can you afford this today?" but "will your *future* balance absorb every instalment?"

```
User proposes purchase (item, price, provider, n_installments, first_date, interest)
        │
        ▼
[Engine 1 — Forecast]  auto_arima refit on user's monthly net-cashflow series
        │  → 3-month projected income/expense/net
        │  → week-by-week projected balance curve
        ▼
[Schedule generator]   builds proposed instalment schedule; overlays it on the curve
        │  → with-purchase curve vs without-purchase curve
        ▼
[Feature engineering]  11-feature vector (incl. forecasted_cash_flow from Engine 1)
        ▼
[Engine 2 — Random Forest + Platt calibration]   calibrated P(high risk) → health score = round((1 − P) × 100)
        ▼
[SHAP TreeExplainer]   top-3 risk-driving factors → plain-language templates
        ▼
Response: score, label (Safe/Caution/At Risk), explanations, recommendation,
          both balance curves, instalment schedule  →  persisted to risk_checks
```

Full serving detail: [ML_SERVING.md](ML_SERVING.md).

## 3. Repository layout (target state)

```
PaySense/
├── docs/                          ← this documentation suite
├── frontend/                      ← Next.js app
│   ├── app/                       (dashboard, transactions, plans, risk-checker routes)
│   ├── components/                (by feature: dashboard/, transactions/, plans/, risk/, ui/)
│   ├── lib/api.ts                 (typed API client — single fetch layer)
│   └── lib/format.ts              (RM currency, date helpers)
├── backend/
│   ├── app/                       (main.py, routers/, services/, db/)
│   ├── models/                    (copied from "models v2/" in Phase 0)
│   ├── scripts/                   (seed.py, smoke_test_models.py)
│   ├── tests/
│   └── requirements.txt
├── models v2/                     ← original trained artefacts (READ-ONLY, never modify)
├── PaySense_Concept_Document.md   ← academic source of truth (never modify)
├── paysense_engine1_forecasting.ipynb   ← provenance (never modify)
├── paysense_engine2_classification.ipynb ← provenance (never modify)
├── farah_spending_history.xlsx    ← seed data source
└── Personal_Finance_Dataset.csv   ← Engine 1 evaluation dataset (not used by the app)
```

## 4. Key data flows

| Flow | Path |
|---|---|
| Dashboard load | `GET /api/dashboard` → one aggregate: balance, month summary, health score, 6-month chart (3 actual + 3 forecast), active plans, alerts |
| Add transaction | Form → `POST /api/transactions` → dashboard/summary re-fetch |
| CSV/PDF import | Upload → `POST /api/import/{csv|pdf}` → **preview only** → user edits/approves → `POST /api/import/confirm` → rows committed |
| Risk check | Form → `POST /api/risk/check` (full pipeline above) → result screen |
| Confirm purchase | `POST /api/risk/confirm` → creates bnpl_plan + instalments, stores risk_score_at_creation |
| Instalment paid | `POST /api/bnpl/plans/{id}/installments/{seq}/pay` → status recompute (active/completed/overdue) |

### 4.1 Current Balance — where it is used

Current Balance is a snapshot stored in `app_state` (one row). It does **not** feed either ML model; it only feeds the projected-balance curve and what is derived from it. (Verified against the code 2026-09-22, revised 2026-09-23 for `ledger_mode`.)

**Two modes, switched by `app_state.ledger_mode` (boolean, default `false`):**

- **`ledger_mode = false` (manual-sync only — the original design, still the default):** Current Balance changes only through Balance Sync (`PUT /api/balance`). No transaction (Income, Expense, Savings) and no BNPL instalment payment changes it.
- **`ledger_mode = true` (running ledger):** every transaction create, edit or delete also moves Current Balance the instant it happens — income adds, expense and savings both subtract (`app/services/ledger.py`). An edit that changes type or amount applies the *difference* between the old and new effect; a delete reverses the original effect. Balance Sync still exists, but becomes a manual correction tool for drift (a missed entry, a bank fee, rounding) rather than the only way the number changes. BNPL instalment payments still don't move it either way — untouched by this change.
  - Auto-adjustment on create/edit/delete does **not** update `balance_synced_at` — that timestamp marks the last time a human confirmed the number against their real bank/cash balance via Balance Sync, not the last time it merely changed from logged activity.
  - Toggling this on is a deliberate, one-time step, not automatic: Farah's plan (2026-09-23) is to finish backfilling historical transactions with `ledger_mode` off (so backfill never touches balance), do one manual sync to set an accurate baseline, then flip `ledger_mode` on for everything logged from that point forward.

| Where | What it does with the balance |
|---|---|
| Dashboard "Current Balance" card | Shows the number and when it was last synced. |
| Balance Sync (`PUT /api/balance`) | Always available; the only update path when `ledger_mode` is off, a correction tool when it's on. |
| `POST/PUT/DELETE /api/transactions`, `POST /api/import/confirm` | Apply the signed delta to Current Balance when `ledger_mode` is on; no-op when it's off. |
| Weekly projected-balance curve (`weekly_balance_curve`, `forecasting.py`) | The starting point, treated as **today's** balance. Each week adds that month's forecast net and subtracts unpaid instalments. |
| Dashboard instalment alerts | "Projected balance may be insufficient" if the curve is below RM0 on an instalment's due date. |
| Risk Checker balance-impact chart | With-purchase and without-purchase curves, plus the RM50 buffer line. |
| Risk Checker extra warning (`low_balance_factor`) | Adds "balance drops below RM50 on [date]" to the top factors. Not a SHAP value. |
| Risk Checker recommendation text (`build_recommendation`) | Wording for Caution ("balance dips to RM X around [date]") and Avoid ("projected deficit of RM X"). A "Safe" verdict always reads "projected balance stays healthy" without checking the curve. |

**Not affected by the balance, in either mode:** Engine 1's ARIMA fit; Engine 2's 11 features, score, label and SHAP; the health speedometer; the month summary; the category breakdown.

**Consequence:** a wrong or stale balance cannot change any ML result — it only changes the curve, dip warnings, recommendation wording and dashboard alerts. Related design note: the forecast-anchoring limitation that also affects the curve is in `PaySense_Concept_Document.md` Section 9 (v12.0), still deferred.

## 5. Deployment target (final phase only — do not build early)

Frontend → Vercel. Backend → Render (uvicorn web service). DB already cloud (Supabase). The only changes needed at deploy time: env-var driven API base URL in the frontend, CORS origin list, and a Render start command — which is why nothing may hardcode `localhost`.
