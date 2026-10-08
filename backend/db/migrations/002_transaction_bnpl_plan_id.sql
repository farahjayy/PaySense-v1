-- Migration: link a transaction to the BNPL plan whose instalment payment logged it.
-- Safe to run against the live, populated Supabase project: it only adds a nullable column
-- and an index. Paste into the Supabase SQL editor and run once, BEFORE restarting the backend.
--
-- on delete set null: deleting a plan keeps its transactions (they just lose the link).
-- Existing rows stay null; link them afterwards with
--   backend/.venv/Scripts/python backend/scripts/backfill_bnpl_plan_id.py --apply

alter table transactions
    add column if not exists bnpl_plan_id uuid references bnpl_plans(id) on delete set null;

create index if not exists idx_transactions_bnpl_plan on transactions (bnpl_plan_id);
