# PaySense — Execution Plan (One-Shot Build)

Build the **entire application in a single pass** — scaffold through polish — then debug and test at the end. Do not pause for confirmation between stages; only stop if genuinely blocked on something only Farah can provide (Supabase credentials) or on an unfixable model-loading failure. Vercel/Render deployment is **excluded** — local-first only.

Never modify: `models v2/`, the two notebooks, `PaySense_Concept_Document.md`, the xlsx/csv datasets.

## Build order (single pass)

The stages below are a dependency order, not gates — flow straight through them.

### Stage 1 — Scaffold
1. `frontend/` (create-next-app, TS, Tailwind, App Router) and `backend/` (FastAPI skeleton, requirements.txt, uvicorn).
2. Copy artefacts `models v2/` → `backend/models/`: both pkls, `engine2_feature_names.npy`, both metadata JSONs, both results CSVs.
3. **Model load check now, not later:** load `engine2_winner.pkl` + the npy once (`scripts/smoke_test_models.py`). This is a build dependency — requirements.txt must pin the library version that unpickles (scikit-learn for the current Random Forest + calibrator). If no version loads it, stop and report; never retrain or stub.
4. Generate `backend/db/schema.sql` (DATABASE.md); ask Farah for Supabase URL + service key and to paste the schema into the Supabase SQL editor — this is the **one allowed pause**; keep building everything that doesn't need the live DB while waiting.
5. `.env.example` both sides, root `.gitignore`, root `README.md`.

### Stage 2 — Backend (complete)
1. Supabase client, Pydantic models, constants module, structured error handling (TECHNICAL.md §4).
2. All endpoints per API_SPEC.md: transactions CRUD + summary, balance, profile, BNPL plans + instalment schedule generator (DATABASE.md §2) + mark-paid + status derivation, dashboard aggregate.
3. ML serving per ML_SERVING.md: `services/forecasting.py` (auto_arima refit, seasonal=False, MA fallback, weekly balance curve), `services/features.py` (11 features, exact npy order, div-by-zero guards), `services/risk.py` (Random Forest + Platt calibration + SHAP TreeExplainer + templates + recommendation), `/api/forecast`, `/api/risk/check`, `/api/risk/confirm`.
4. Imports per API_SPEC.md §6: CSV preview/confirm with category guessing, PDF via pdfplumber (graceful 422 on failure), `sample_statement.csv` fixture.
5. `scripts/seed.py` per DATABASE.md §4 — inspect the real xlsx structure before writing the parser.

### Stage 3 — Frontend (complete)
1. Design tokens in Tailwind config, layout shell + nav, `lib/api.ts` typed client, `lib/constants.ts`, `lib/format.ts`.
2. UI kit (UI_SPEC §4), then all four screens per UI_SPEC §3: Dashboard (balance, mini-cards, speedometer, 6-month chart, BNPL list, alerts, CTA), Transactions (list/filters/form/breakdown + CSV/PDF import flow), BNPL Plans (cards, create with live schedule preview, detail timeline), Risk Checker (form → staged loading → score hero, recommendation banner, overlay chart, SHAP panel, schedule, confirm/discard).
3. Every screen gets loading/empty/error states (UI_SPEC §5) as it's built — these are part of the build, not the test phase.

### Stage 4 — Verification & debugging (after everything is built)
1. Run `scripts/seed.py`; fix whatever breaks against the real xlsx.
2. Boot both servers; drive the full demo path end-to-end: dashboard → add transaction → create plan → CSV import (fixture) → risk check → confirm → plan appears with risk badge. Debug until it works.
3. Write and run the pytest suite per TESTING.md (schedule math, feature vector, score buckets, forecasting fallback, status derivation, API round-trips). Fix implementation, not tests.
4. Manual checklist from TESTING.md §4: responsive 375/768/1440, error/empty states, PDF failure path, currency formatting, refresh on every route.
5. Final: remove debug output, README complete, conventional commits (logical commits per stage are fine — e.g. `feat: backend`, `feat: frontend`, `test: ...`, `fix: ...`).

### Excluded — Phase 6 deployment (Vercel/Render)
Only when Farah explicitly asks, later. Nothing may hardcode `localhost` (env-driven URLs) so this stays a config-only change.

## Working rules

- If the docs are ambiguous or contradict reality (e.g. xlsx layout differs from the seed spec), inspect the real data first, then ask rather than guess.
- Deliver a final report at the end: what was built, test results, anything deferred or fragile, and exact commands for Farah to run the app.
- Prefer boring, working code over cleverness; this is an FYP demo whose reliability is the grade.
