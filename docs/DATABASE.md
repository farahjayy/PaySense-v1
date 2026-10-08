# PaySense — Database Specification (Supabase PostgreSQL)

Single-user demo: **no user table, no user_id columns, no RLS policies needed**. Backend connects with the service_role key. Generate this schema as `backend/db/schema.sql` for pasting into the Supabase SQL editor (make it idempotent: `drop table if exists ... cascade` guarded blocks or `create table if not exists`).

## 1. Tables

### transactions
| Column | Type | Notes |
|---|---|---|
| id | uuid pk default gen_random_uuid() | |
| date | date not null | transaction date |
| amount | numeric(12,2) not null check (amount > 0) | always positive; direction from `type` |
| type | text not null check (type in ('income','expense')) | |
| category | text not null | e.g. Food, Transport, Rent, Salary, Allowance, Shopping, Bills, Entertainment, Education, Other |
| description | text | |
| account_name | text | e.g. "Maybank", "TnG eWallet" |
| is_bnpl | boolean not null default false | true if this expense is a BNPL instalment payment |
| bnpl_plan_id | uuid null references bnpl_plans(id) on delete set null | the plan whose instalment payment logged this transaction (migration `002_transaction_bnpl_plan_id.sql`). Set by "mark paid"; null for hand-typed and older rows. Deleting a plan keeps its transactions and just clears the link |
| source | text not null default 'manual' check (source in ('manual','csv','pdf','seed')) | import provenance |
| created_at | timestamptz not null default now() | |

Index: `(date desc)`, `(category)`, `(type)`.

### bnpl_plans
| Column | Type | Notes |
|---|---|---|
| id | uuid pk | |
| item_name | text not null | |
| provider | text not null | SPayLater, TikTok PayLater, Atome, Other (GrabPayLater and PayLater by Boost were dropped 2026-09-26; existing rows keep their text) |
| total_price | numeric(12,2) not null check (total_price > 0) | |
| interest_rate | numeric(5,2) not null default 0 | the provider's **monthly fee, % per month** (changed 2026-09-26 from a whole-plan flat %; column name unchanged). Total = price × (1 + rate/100 × instalments) |
| num_installments | int not null check (num_installments between 1 and 36) | |
| first_payment_date | date not null | the resolved first due date: the provider's rule applied to the purchase date, or the user's override |
| status | text not null default 'active' check (status in ('active','completed','overdue')) | derived — see §3 |
| risk_score_at_creation | int | null when plan created manually without a risk check |
| created_at | timestamptz not null default now() | |

### bnpl_installments
| Column | Type | Notes |
|---|---|---|
| id | uuid pk | |
| plan_id | uuid not null references bnpl_plans(id) on delete cascade | |
| seq | int not null | 1-based |
| due_date | date not null | monthly from first_payment_date |
| amount | numeric(12,2) not null | see §2 |
| is_paid | boolean not null default false | |
| paid_date | date | |

Unique: `(plan_id, seq)`.

### risk_checks
| Column | Type | Notes |
|---|---|---|
| id | uuid pk | |
| input | jsonb not null | the purchase form payload |
| feature_vector | jsonb not null | the 11 features as sent to the Engine 2 Random Forest (auditability for the FYP report) |
| risk_probability | numeric(6,5) not null | raw P(high risk) |
| risk_score | int not null | health score 0–100 |
| label | text not null check (label in ('safe','caution','at_risk')) | |
| top_factors | jsonb not null | array of {feature, shap_value, message} |
| recommendation | text not null | |
| created_at | timestamptz not null default now() | |

### app_state (single row, id = 1)
| Column | Type | Notes |
|---|---|---|
| id | int pk check (id = 1) | enforce single row |
| current_balance | numeric(12,2) not null | |
| balance_synced_at | timestamptz not null default now() | |
| profile | jsonb not null default '{"age": 22, "employment_status": 0}' | employment encoding: 0=student, 1=employed, 2=self-employed, 3=unemployed (must match Engine 2 training — see ML_SERVING.md) |

## 2. Instalment schedule generation (backend `services/schedule.py`)

```
total_payable   = total_price × (1 + interest_rate/100 × num_installments)   -- integer sen, rounded half up to the sen
instalment(seq) = floor(total_payable / num_installments) in sen; the LAST instalment takes the leftover sen
base_amount     = round(total_payable / num_installments, 2)
last_amount     = total_payable − base_amount × (num_installments − 1)   # absorbs rounding
due_date(seq)   = first_payment_date + (seq − 1) months
first_payment_date = user override, else by provider (docs/BNPL Billing Rules ...md): SPayLater and TikTok PayLater: nothing at checkout, first bill assumed one month after the purchase, same day (one uniform, clearly-flagged assumption); Atome: first payment on the purchase date, charged at checkout and stored as already paid; Other: purchase date, nothing prepaid.
seq 1 is inserted with is_paid = true, paid_date = due_date when it is charged at checkout (Atome)
```
The rounding rule matters: the sum of instalments must equal total_payable exactly. Unit-test this (TESTING.md).

## 3. Plan status derivation (computed on read + on instalment payment)

- `completed` — all instalments paid.
- `overdue` — any unpaid instalment with due_date < today.
- `active` — otherwise.

## 4. Seed specification (`backend/scripts/seed.py` — idempotent: wipe all tables, then insert)

1. **Transactions from `farah_spending_history.xlsx`** (repo root): 12 monthly sheets, May 2025 – Apr 2026, real RM amounts. Parse with openpyxl. Known quirk: **date cells arrive as Python datetime objects, not numeric serials** — handle both. Inspect the sheet structure first (`python -c` dump of one sheet) before writing the parser; map each row to (date, amount, type, category, description), `source='seed'`.
2. **Two active BNPL plans** with realistic Malaysian data, e.g. SPayLater phone accessory RM 899 × 6 from ~2 months ago (2 instalments already paid) and Atome sneakers RM 429 × 3 from ~3 weeks ago (1 paid). Generate instalments per §2; mark past ones paid so status logic shows life.
3. **app_state**: current_balance ≈ RM 1,850.00, default profile.
4. Print a summary (rows inserted per table) at the end.
