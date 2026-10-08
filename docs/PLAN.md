# PaySense — Project Plan

**Project:** PaySense — AI-Driven System for Financial Health Forecasting and BNPL Risk Classification (FYP2, UTP)
**Owner:** Farah (farahjayy/PaySense)
**Stage:** Application development. Both ML engines are trained, evaluated, and serialised — this phase builds the product around them.

## Goal

A fully working, demo-ready responsive web application where a Malaysian Gen-Z student can:
1. See their financial health at a glance (balance, health score, 6-month history + AI forecast).
2. Manage transactions (manual entry, CSV import, PDF bank statement import).
3. Track BNPL plans and instalments.
4. **Check a proposed BNPL purchase before committing** — the flagship flow: the app forecasts their future balance (Engine 1), scores the purchase risk (Engine 2), explains it in plain language (SHAP), and recommends an action.

## Locked decisions

| Decision | Value |
|---|---|
| Users | Single-user demo. No auth, no user_id columns. |
| Scope | Full concept-doc scope: 4 screens incl. CSV + PDF import. |
| Runtime | Local-first: both apps on localhost; DB is Supabase cloud free tier. Vercel/Render deployment is a final, separate phase. |
| Engine 1 winner | ARIMA (RMSE 7,300.30) — refit via `auto_arima(seasonal=False)` on user data at serve time. |
| Engine 2 winner | Random Forest + Platt (sigmoid) calibration (5×5 repeated-CV: F1 0.826, ROC-AUC 0.868, Brier 0.146) — pkls loaded at serve time + SHAP TreeExplainer. Hand-set, untuned hyperparameters for all candidates. |
| Model artefacts | Already in repo at `models v2/`; copied to `backend/models/` in Phase 0. |
| Seed data | `farah_spending_history.xlsx` (12 sheets, May 2025 – Apr 2026, real RM amounts). |

## Document map

| Document | Contents |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture, sequential AI pipeline, repo layout, data flow |
| [TECHNICAL.md](TECHNICAL.md) | Stack, dependencies, environment variables, coding standards, error-handling policy |
| [DATABASE.md](DATABASE.md) | Full PostgreSQL schema, table semantics, seed-data specification |
| [API_SPEC.md](API_SPEC.md) | Every endpoint with request/response shapes |
| [ML_SERVING.md](ML_SERVING.md) | Engine 1 + Engine 2 serving design, feature engineering, SHAP explanation mapping |
| [UI_SPEC.md](UI_SPEC.md) | Design tokens, screen-by-screen component specs |
| [EXECUTION.md](EXECUTION.md) | One-shot build order (scaffold → backend → frontend → end-stage verification) |
| [TESTING.md](TESTING.md) | Test strategy, required test cases, verification commands |

Root-level references: `PaySense_Concept_Document.md` (academic source of truth), `paysense_dashboard_mockup.html` (visual reference), the two training notebooks (ML provenance).

**Precedence:** if these docs conflict with the concept document, the docs win. If docs conflict with each other, EXECUTION.md wins for sequencing and the domain doc (API_SPEC / ML_SERVING / DATABASE / UI_SPEC) wins for its own domain.

## Success criteria

- Full click-through demo on localhost with real seeded data — no blank screens, no unhandled errors.
- Risk Checker returns a score + SHAP explanation + overlay chart in under ~5 seconds.
- End-stage verification (EXECUTION.md Stage 4) passes: seeded demo path works end-to-end, test suite green.
- Test suite green; feature-vector construction and instalment schedule generation covered by unit tests.
- README that lets an FYP evaluator run the project from scratch.
