# PaySense — Technical Standards

## 1. Stack & dependencies

### Frontend (`frontend/`)
| Concern | Choice |
|---|---|
| Framework | Next.js 14+ (App Router) + TypeScript, strict mode |
| Styling | Tailwind CSS (tokens in `tailwind.config` — see UI_SPEC.md) |
| Charts | Recharts (bar chart, line/area overlay, gauge built from RadialBar or custom SVG) |
| Data fetching | Native fetch through one typed client `lib/api.ts`; no state library needed at this scale — server components + a few client hooks |
| Forms | Controlled components with inline validation; no heavy form library required |

### Backend (`backend/`)
| Concern | Choice |
|---|---|
| Framework | FastAPI + uvicorn, Python 3.11 |
| ML runtime | `pmdarima` (Engine 1 refit), `scikit-learn` (Engine 2 Random Forest + calibrator pkls), `shap`, `numpy`, `pandas` |
| DB client | `supabase` (supabase-py), service_role key, server-side only |
| File parsing | `pandas` (CSV), `pdfplumber` (PDF), `openpyxl` (seed xlsx) |
| Validation | Pydantic v2 models for every request/response body |
| Tests | `pytest` + `httpx` AsyncClient |

**Version pinning:** `models v2/` metadata does NOT record training library versions (Colab defaults, July 2026). Rule: pin whatever versions successfully pass `scripts/smoke_test_models.py` (loads `engine2_winner.pkl` + `engine2_feature_names.npy`, runs one dummy prediction). If unpickling fails, adjust the `scikit-learn` version (the current Engine 2 artefacts are scikit-learn objects) until it loads; if that fails, STOP and report — never silently retrain or stub. `engine1_winner.pkl` is provenance only and does not need to load in the app environment.

## 2. Environment variables

`backend/.env` (git-ignored; ship `.env.example`):
```
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
CORS_ORIGINS=http://localhost:3000
```
`frontend/.env.local` (git-ignored; ship `.env.example`):
```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```
Validate required vars at startup (backend: fail fast with a clear message if missing). Never commit real keys. Never hardcode URLs — everything through env.

## 3. Coding standards

- **Files:** small and focused — target 200–400 lines, hard max 800. Organise by feature/domain, not by type.
- **Functions:** < 50 lines, early returns over deep nesting (max 4 levels).
- **Immutability:** return new objects; don't mutate inputs (both TS and Python service code).
- **Naming:** TS `camelCase` vars / `PascalCase` components; Python `snake_case`; constants `UPPER_SNAKE_CASE`. Booleans prefixed `is/has/should`.
- **No magic numbers:** thresholds (health-score buckets, RM50 low-balance threshold, 7-day alert window, forecast horizon) live in one constants module per app.
- **No debug output:** no `console.log` in committed frontend code; backend uses `logging`, not `print`.
- **Comments:** only for non-obvious constraints (e.g. why seasonal=False in ARIMA). No narration.

## 4. Error-handling policy

- **Backend:** every router wraps service errors into structured HTTP errors: `{ "detail": { "code": "FORECAST_INSUFFICIENT_DATA", "message": "..." } }`. Expected failures (bad upload, unparseable PDF, <3 months of data) are 4xx with actionable messages; only genuine bugs are 500. ML/pickle/DB failures at startup fail fast and loud.
- **Frontend:** every fetch through `lib/api.ts` which normalises errors; every screen has loading (skeleton), empty, and error states. An API failure shows a readable toast/banner — **never a blank screen or raw stack trace**.
- **Imports:** parse failures return a friendly "couldn't parse this file — try CSV export instead" 422, never a 500.

## 5. Validation at boundaries

- All request bodies validated by Pydantic (amounts > 0, dates valid ISO, type ∈ {income, expense}, instalments 1–36, interest 0–30%).
- Frontend mirrors the same rules inline before submit (fast feedback), but the backend is the authority.
- File uploads: cap 5 MB, extension + content sniff, reject others with 422.

## 6. Domain constants (single source: `backend/app/constants.py` + mirrored `frontend/lib/constants.ts`)

| Constant | Value |
|---|---|
| `HEALTH_SAFE_MIN` | 70 |
| `HEALTH_CAUTION_MIN` | 40 |
| `LOW_BALANCE_THRESHOLD_RM` | 50 |
| `ALERT_WINDOW_DAYS` | 7 |
| `FORECAST_MONTHS` | 3 |
| `HISTORY_MONTHS_SHOWN` | 3 |
| `MIN_MONTHS_FOR_ARIMA` | 3 |
| `DEFAULT_PROFILE` | age 22, employment_status 0 (student) |

## 7. Git conventions

Conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`), one commit per completed phase minimum. Never commit `.env`, `node_modules`, `__pycache__`, `.next`. Root `.gitignore` covers both apps. Model pkls in `backend/models/` ARE committed (small, needed to run).
