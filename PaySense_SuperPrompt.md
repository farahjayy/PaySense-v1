# PaySense — Super Prompt for Claude Code (One-Shot Build)

> Paste everything below this line into a fresh Claude Code session, run from the repo root (`FYP/PaySense`).

---

You are building **PaySense**, my Final Year Project (UTP): an AI-driven financial copilot that helps Malaysian Gen-Z students avoid BNPL (Buy Now Pay Later) debt. The two ML engines are **already trained and serialised** — ARIMA for cash-flow forecasting (Engine 1) and XGBoost for BNPL risk classification (Engine 2), linked sequentially so the forecast becomes the risk model's evaluation context. Your job is to build the complete web application around them **in one shot**: the full backend, full frontend, and seed data, then debug and test everything at the end. Do not build in confirmation-gated phases.

## Read these first, in this order

1. `docs/PLAN.md` — goals, locked decisions, document map, precedence rules
2. `docs/ARCHITECTURE.md` — system design, sequential AI pipeline, target repo layout
3. `docs/EXECUTION.md` — **the one-shot build order**: scaffold → complete backend → complete frontend → verification/debugging at the end
4. Then, as needed while building: `docs/TECHNICAL.md` (stack, standards, env, error policy), `docs/DATABASE.md` (schema + seed spec), `docs/API_SPEC.md` (every endpoint with shapes), `docs/ML_SERVING.md` (engine serving, 11-feature spec, SHAP mapping), `docs/UI_SPEC.md` (design tokens + screen specs), `docs/TESTING.md` (test suite to write and run at the end)

Background references (read-only, never modify): `PaySense_Concept_Document.md`, `paysense_dashboard_mockup.html`, the two `.ipynb` notebooks, `models v2/`, `farah_spending_history.xlsx`, `Personal_Finance_Dataset.csv`.

## Non-negotiable rules

- **One-shot build:** work straight through the stages in `docs/EXECUTION.md` without stopping for my confirmation. Debugging and the test suite come AFTER everything is built (Stage 4). The only allowed pause: asking me for the Supabase URL + service_role key after you generate `schema.sql` — and keep building everything that doesn't need the live DB while you wait.
- Single-user demo — no auth, no user_id anywhere.
- **Local-first — do NOT set up Vercel or Render.** Deployment is excluded from this build entirely; keep all URLs env-driven so it stays a config-only change later.
- The docs in `docs/` are the source of truth; they override the concept document. If a doc is ambiguous or contradicts reality (e.g. the xlsx layout differs from the seed spec), inspect the real file first, then ask me — never guess silently.
- Model artefacts: copy from `models v2/` to `backend/models/` during scaffolding, and verify the XGBoost pickle loads immediately (it's a build dependency for requirements.txt version pinning). If no xgboost version unpickles it, stop and report — never retrain or stub the models.
- The `employment_status` encoding (0=student, 1=employed, 2=self-employed, 3=unemployed) and the 11-feature order in `engine2_feature_names.npy` are fixed by training — serving must match exactly.
- Errors surface as readable messages in the UI — never a blank screen, never a raw 500 for an expected failure.
- Conventional commits at logical points (e.g. `feat: backend`, `feat: frontend`, `test: ...`). Never commit `.env` or secrets.

## When you finish

Deliver a final report: what was built, seed + test results, the exact commands I run to start the app, and anything deferred or fragile. The app must survive the full demo path: dashboard → add transaction → create plan → CSV import → risk check → confirm → plan appears with its risk badge.

Start now.
