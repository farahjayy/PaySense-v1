# PaySense — Application Development Plan

**Date:** 16 July 2026 | **Stage:** FYP2 — Application Development
**Decisions locked:** Single-user demo (no auth) · Full concept-doc scope · Local-first (Supabase cloud DB, app on localhost) · Deploy to Vercel/Render as final phase

---

## 0. Prerequisites (do these BEFORE running the super prompt)

1. **Model artefacts — ✅ already in the repo.**
   The `models v2/` folder (repo root) contains everything: `engine1_winner.pkl`, `engine1_metadata.json`, `engine2_winner.pkl`, `engine2_feature_names.npy`, `engine2_metadata.json`, results CSVs, and all evaluation plots. Claude Code will copy the needed files into `backend/models/` during Phase 0 — nothing for you to download.
2. **Create a Supabase project** (free tier) at [supabase.com](https://supabase.com) → note the Project URL and `anon`/`service_role` keys. Claude Code will create the tables via SQL.
3. **Install locally:** Node.js 20+, Python 3.11, Git (already have).

---

## 1. Architecture Recap

```
frontend/  Next.js (App Router) + Tailwind + Recharts   → localhost:3000 → later Vercel
backend/   FastAPI + pmdarima + scikit-learn + shap + pandas → localhost:8000 → later Render
database   Supabase (PostgreSQL, cloud free tier)
```

Sequential AI flow (core novelty): **Engine 1 forecast → feature vector (incl. `forecasted_cash_flow`) → Engine 2 Random Forest (calibrated) → SHAP → risk score + explanation.**

## 2. Key Technical Decisions

| Concern | Decision |
|---|---|
| Auth | None. Single implicit user; all tables have no `user_id`. |
| ARIMA serving | The saved ARIMA was fitted on Kaggle data. At inference, **refit `auto_arima(seasonal=False, stepwise=True)` on the demo user's own monthly net-cashflow series** — exactly the pattern already validated in notebook cell 34 (seasonal disabled because personal data has <12 months). The .pkl is kept as the empirical evaluation artefact. |
| Balance curve | Deterministic overlay: current balance + weekly-spread forecasted net flow − scheduled BNPL instalments on their due dates. |
| Risk score | Health score = (1 − P(high risk)) × 100. Safe 70–100 / Caution 40–69 / At Risk 0–39. |
| SHAP | TreeExplainer on the Random Forest at inference; top-3 features mapped to plain-language templates. |
| Version safety | Metadata JSONs do **not** record library versions (trained on Colab defaults, July 2026). Phase 2 starts with a smoke-test script that loads `engine2_winner.pkl` + `engine2_feature_names.npy` and runs one prediction; if unpickling fails, adjust the `scikit-learn` version until it loads — and report rather than silently stubbing. |
| Seed data | Import `farah_spending_history.xlsx` (12 sheets, May 2025–Apr 2026) via a seed script so the demo shows real data on first launch. |

## 3. Build Phases

| Phase | Deliverable | Demo checkpoint |
|---|---|---|
| **0. Scaffold** | Monorepo (`frontend/` + `backend/`), env files, Supabase schema SQL applied | Both dev servers boot |
| **1. Backend core** | Transaction + BNPL plan CRUD, balance sync, seed script from your xlsx | API returns your real data in Swagger docs |
| **2. ML serving** | `/forecast` (Engine 1), `/risk/check` (sequential Engine 1→2 + SHAP), model loader with version checks | Risk check returns score + top-3 factors via Swagger |
| **3. Frontend** | All 4 screens: Dashboard (speedometer, 6-month chart, alerts), Transactions, BNPL Plans Manager, Risk Checker (overlay chart + SHAP panel) | Full click-through demo on localhost |
| **4. Imports** | CSV import with preview/confirm; PDF import (pdfplumber, Maybank/CIMB/RHB best-effort) | Upload a statement, see parsed preview |
| **5. Polish** | Empty/error/loading states, responsive pass, README, tests for feature-engineering + risk pipeline | FYP-presentation-ready |
| **6. Deploy (later)** | Vercel (frontend) + Render (backend), env vars, CORS | Public URL for evaluators |

## 4. How to use the super prompt

1. Complete the prerequisites above (models in `backend/models/`, Supabase keys ready).
2. Open Claude Code in this repo and paste the contents of `PaySense_SuperPrompt.md`.
3. Build proceeds phase by phase — each phase ends with a working, testable state. Verify each checkpoint before letting it continue.
