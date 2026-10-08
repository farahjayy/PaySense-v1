-- Migration: add the 'savings' transaction type and the ledger_mode toggle.
-- Unlike schema.sql (which drops and recreates everything), this is safe to
-- run against the live, populated Supabase project — it only alters, never drops.
-- Paste into the Supabase SQL editor and run once.

alter table transactions drop constraint if exists transactions_type_check;
alter table transactions add constraint transactions_type_check
    check (type in ('income', 'expense', 'savings'));

alter table app_state add column if not exists ledger_mode boolean not null default false;
