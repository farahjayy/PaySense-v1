# PaySense — API Specification (FastAPI, prefix `/api`)

All responses JSON. Errors: `{ "detail": { "code": "MACHINE_CODE", "message": "human readable" } }`. Amounts are numbers in RM. Dates ISO `YYYY-MM-DD`.

## 1. Dashboard

### GET /api/dashboard
One aggregate call powering the whole dashboard screen.
```jsonc
{
  "current_balance": 1850.00,
  "balance_synced_at": "2026-07-16T08:00:00Z",
  "month_summary": { "income": 1200.00, "expenses": 940.50, "month": "2026-07" },
  "health": { "score": 62, "label": "caution" },          // from latest risk context — see ML_SERVING.md §4
  "chart": [                                                // 6 entries: 3 historical + 3 forecast
    { "month": "2026-05", "income": 1200, "expenses": 980, "is_forecast": false },
    { "month": "2026-08", "income": 1180, "expenses": 1010, "is_forecast": true }
  ],
  "forecast_method": "arima",                               // or "fallback_ma"
  "active_plans": [ { "id": "...", "item_name": "...", "provider": "...", "installment_amount": 149.83, "remaining_total": 449.49, "remaining_installments": 4, "next_due_date": "2026-08-01" } ],
                                                             // sorted by next_due_date ascending (soonest/most overdue first; nothing-left-due sorts last)
  "bnpl_summary": { "plan_count": 3, "overdue_total": 10.00, "upcoming_total": 53.03 },
                                                             // every unpaid instalment across open plans, split by whether its due date has passed
  "alerts": [ { "plan_id": "...", "item_name": "...", "amount": 149.83, "due_date": "2026-07-20", "projected_balance_sufficient": false } ]
}
```
Alerts = unpaid instalments due within 7 days; `projected_balance_sufficient` compares against Engine 1's balance curve. `active_plans` is returned for API completeness; the Dashboard screen itself only uses `bnpl_summary` (see UI_SPEC.md §3.1) — the per-plan list lives on the Plans page.

## 2. Balance

- **GET /api/balance** → `{ "current_balance": ..., "balance_synced_at": ... }`
- **PUT /api/balance** body `{ "current_balance": 2000.00 }` → updated object. (Balance Sync feature.)

## 3. Transactions

- **GET /api/transactions?month=2026-07&category=Food&type=expense&search=grab&limit=50&offset=0** → `{ "items": [...], "total": 123 }`
- **POST /api/transactions** body `{ date, amount, type, category, description?, account_name?, is_bnpl? }` → created row (201)
- **PUT /api/transactions/{id}** partial update → updated row
- **DELETE /api/transactions/{id}** → 204
- **GET /api/transactions/summary?month=2026-07** →
  `{ "income": ..., "expenses": ..., "by_category": [ { "category": "Food", "total": 320.00, "pct": 34.0 } ] }`

## 4. BNPL plans

- **GET /api/bnpl/plans?status=active** → list; each with computed `installment_amount`, `paid_count`, `remaining_count`, `next_due_date`, derived `status`
- **POST /api/bnpl/plans** body `{ item_name, provider, total_price, interest_rate, num_installments, purchase_date?, first_payment_date? }` (`interest_rate` is the monthly fee, % per month) → creates plan **and** its instalment schedule (DATABASE.md §2); returns plan with instalments (201). `purchase_date` defaults to today; the first due date follows the provider's rule unless `first_payment_date` overrides it. Atome's checkout payment is stored as already paid and subtracted from the balance now (the later instalments are subtracted when marked paid).
- **GET /api/bnpl/plans/{id}** → plan + full instalment timeline + risk_score_at_creation
- **POST /api/bnpl/plans/{id}/installments/{seq}/pay** (subtracts the instalment amount from Current Balance, in every ledger mode, even when no transaction is logged) body `{ paid_date? }` (default today) → marks paid, optionally auto-creates a matching `is_bnpl=true` expense transaction (flag `create_transaction: true` default), recomputes plan status
- **GET /api/bnpl/bills** → `{ "months": [ { "month": "2026-09", "is_current": true, "total_due": 15.63, "paid_total": 5.63, "fully_paid": false, "has_overdue": false, "items": [ { "plan_id": "...", "item_name": "...", "provider": "...", "seq": 2, "amount": 5.63, "due_date": "2026-09-16", "is_paid": true } ] } ] }`. Every instalment across every plan (any status), grouped by due month. Order: the current month first (only if something is actually due in it — no synthetic RM0 row), then past months going backward, then upcoming months going forward. `fully_paid` requires every instalment in that month to be paid; `has_overdue` is true if any unpaid instalment's due date has passed
- **PATCH /api/bnpl/plans/{id}** body `{ item_name }` (required) → the updated plan. Renames the plan at any time; nothing else is editable (any other field is `422`; to change price, fee, instalments or dates, delete the plan and create a new one). The descriptions of the plan's linked transactions are renamed with it (a description the user rewrote is left alone). No amount, date, balance or instalment changes
- **GET /api/bnpl/plans/{id}/transactions** → `{ count, total, items:[{id,date,amount,description}] }`: the transactions linked to this plan by `transactions.bnpl_plan_id` (logged when its instalments were marked paid). Text is never used to decide what belongs to a plan
- **DELETE /api/bnpl/plans/{id}?delete_transactions=false** → 200 `{ deleted_transactions, failed_transactions }` (cascade instalments). Transactions are **kept** unless `delete_transactions=true`, in which case exactly the transactions linked to the plan are deleted and their amounts are given back to the balance

## 5. ML endpoints

### GET /api/forecast
Engine 1. Response:
```jsonc
{
  "method": "arima",                       // "fallback_ma" if <3 months of data
  "monthly": [ { "month": "2026-08", "income": 1180.0, "expenses": 1010.0, "net": 170.0 } ],  // 3 forecast months
  "balance_curve": [ { "date": "2026-07-20", "balance": 1712.4 } ],   // weekly, 3 months ahead, instalments applied on due dates
  "low_balance_dates": [ { "date": "2026-08-10", "balance": 32.5 } ]  // points below RM50 threshold
}
```

### POST /api/risk/check
The sequential Engine 1 → Engine 2 pipeline (ML_SERVING.md). Body:
`{ item_name, total_price, provider, num_installments, purchase_date?, first_payment_date?, interest_rate }` (`interest_rate` = monthly fee, % per month) (`first_payment_date` is an optional override of the provider's rule; each `proposed_schedule` item carries `paid_at_checkout`)
Response:
```jsonc
{
  "check_id": "...",
  "risk_probability": 0.38,
  "score": 62, "label": "caution",
  "top_factors": [ { "feature": "num_bnpl_plans", "shap_value": 0.21, "message": "You already have 2 active BNPL plans" } ],
  "recommendation": "Consider delaying this purchase by 3 weeks — your balance dips below RM50 on 10 Aug.",
  "curves": {
    "without_purchase": [ { "date": "...", "balance": ... } ],
    "with_purchase":    [ { "date": "...", "balance": ... } ]
  },
  "proposed_schedule": [ { "seq": 1, "due_date": "2026-08-01", "amount": 149.83 } ]
}
```

### POST /api/risk/confirm
Body `{ "check_id": "..." }` → creates the BNPL plan + instalments from that check's stored input, sets `risk_score_at_creation`. Returns the created plan (201). 404 if check_id unknown; 409 if already confirmed.

## 6. Imports

- **POST /api/import/csv** (multipart file) → **preview only, no writes**:
  `{ "import_id": "...", "rows": [ { "row": 1, "date": "...", "amount": ..., "type": "expense", "category_guess": "Food", "description": "...", "issues": [] } ], "skipped": [ { "row": 7, "reason": "unparseable date" } ] }`
  Category guess via keyword rules (grab/food/mcd → Food; tng/petrol → Transport; etc.). Store the preview server-side (in-memory dict keyed by import_id is fine for the demo).
- **POST /api/import/pdf** (multipart file) → same preview shape. pdfplumber, best-effort table/line extraction for Maybank, CIMB, RHB statement layouts. If nothing parseable: 422 `PDF_PARSE_FAILED` with message "couldn't read this statement — try CSV export from your bank instead".
- **POST /api/import/confirm** body `{ "import_id": "...", "rows": [ ...user-edited rows... ] }` → validates and inserts with `source='csv'|'pdf'` → `{ "inserted": 42 }`.

## 7. Profile (for Engine 2 demographics)

- **GET /api/profile** → `{ "age": 22, "employment_status": 0 }`
- **PUT /api/profile** body same shape (age 18–30, employment_status 0–3) → updated. Stored in `app_state.profile`.
