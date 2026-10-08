> **PaySense v1 — public archive.** This is the first prototype of PaySense, built during FYP1 and early FYP2 (Universiti Teknologi PETRONAS). It is **superseded by [PaySense-v2](https://github.com/farahjayy/PaySense-v2)**, which redesigns both engines based on the lessons recorded here.
>
> This public copy is sanitized: the author's real transaction spreadsheets, working status notes that contained personal financial details, and private correspondence are removed, and notebook outputs are stripped. The app's seed script expects a personal spreadsheet that is therefore not included — v1 will not run with demo data out of the box. The Kaggle dataset used for Engine 1 evaluation is available at https://www.kaggle.com/datasets/ramyapintchy/personal-finance-data.

---

# PaySense

**AI-Driven System for Financial Health Forecasting and BNPL Risk Classification**
Final Year Project (FYP2), Universiti Teknologi PETRONAS — Farah.

PaySense is a financial copilot for Malaysian Gen-Z students. It forecasts your
cash flow with ARIMA (Engine 1), then scores any proposed BNPL purchase with
Random Forest + SHAP (Engine 2) — the two engines run **in sequence**, so the risk
score is evaluated against your *future* balance, not just today's.

```
Next.js (localhost:3000) → FastAPI (localhost:8000) → Supabase (cloud PostgreSQL)
                                 │
                                 ├─ Engine 1: auto_arima refit on your transactions
                                 └─ Engine 2: trained Random Forest (+ Platt calibration) + SHAP TreeExplainer
```

## Prerequisites

- Python 3.11+ (developed on 3.14)
- Node.js 20+
- A free [Supabase](https://supabase.com) project

## Setup (once)

### 1. Database

1. Create a Supabase project → SQL Editor → paste and run `backend/db/schema.sql`.
2. Project Settings → API: copy the **URL** and the **service_role key**.

### 2. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt     # Windows
cp .env.example .env                               # then fill in SUPABASE_URL + SUPABASE_SERVICE_KEY
.venv\Scripts\python scripts\smoke_test_models.py  # must print "SMOKE TEST PASSED"
.venv\Scripts\python scripts\seed.py               # loads 12 months of demo data
```

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
```

## Run (every time)

Two terminals:

```bash
# Terminal 1 — backend
cd backend
.venv\Scripts\uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm run dev
```

Open http://localhost:3000.

## Demo path

Dashboard → add a transaction → create a plan → import `backend/scripts/fixtures/sample_statement.csv`
→ Risk Checker: check a purchase → Confirm & Save → the plan appears with its risk badge.

## Tests

```bash
cd backend
.venv\Scripts\python -m pytest -q
```

## Repository map

| Path | Contents |
|---|---|
| `docs/` | Full specification suite (architecture, API, ML serving, UI, testing) |
| `backend/` | FastAPI app, ML serving, seed script, tests |
| `backend/models/` | Serving copies of the trained artefacts |
| `frontend/` | Next.js app (App Router, Tailwind, Recharts) |
| `models v2/` | Original training artefacts — **read-only provenance** |
| `paysense_engine*.ipynb` | Training notebooks — **read-only provenance** |
| `farah_spending_history.xlsx` | Real 12-month personal spending data (seed source) |

## Notes

- Single-user demo: no auth, by design (see `docs/PLAN.md`).
- `scikit-learn` is pinned to **1.7.2** — the version that unpickles `engine2_winner.pkl` and
  `engine2_calibrator.pkl`. If you change it, run the smoke test before anything else.
- Deployment (Vercel/Render) is deliberately excluded; all URLs are env-driven
  so it stays a config-only change later.
