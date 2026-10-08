-- PaySense schema (Supabase PostgreSQL) — single-user demo, no auth/RLS.
-- Idempotent: safe to paste into the Supabase SQL editor repeatedly.

drop table if exists risk_checks cascade;
drop table if exists bnpl_installments cascade;
drop table if exists bnpl_plans cascade;
drop table if exists transactions cascade;
drop table if exists app_state cascade;

create table transactions (
    id uuid primary key default gen_random_uuid(),
    date date not null,
    amount numeric(12,2) not null check (amount > 0),
    type text not null check (type in ('income', 'expense', 'savings')),
    category text not null,
    description text,
    account_name text,
    is_bnpl boolean not null default false,
    source text not null default 'manual' check (source in ('manual', 'csv', 'pdf', 'seed')),
    created_at timestamptz not null default now()
);

create index idx_transactions_date on transactions (date desc);
create index idx_transactions_category on transactions (category);
create index idx_transactions_type on transactions (type);

create table bnpl_plans (
    id uuid primary key default gen_random_uuid(),
    item_name text not null,
    provider text not null,
    total_price numeric(12,2) not null check (total_price > 0),
    interest_rate numeric(5,2) not null default 0,
    num_installments int not null check (num_installments between 1 and 36),
    first_payment_date date not null,
    status text not null default 'active' check (status in ('active', 'completed', 'overdue')),
    risk_score_at_creation int,
    created_at timestamptz not null default now()
);

-- A transaction logged by paying a plan's instalment points back at that plan.
-- (Added after bnpl_plans exists; deleting a plan keeps its transactions, unlinked.)
alter table transactions
    add column bnpl_plan_id uuid references bnpl_plans(id) on delete set null;
create index idx_transactions_bnpl_plan on transactions (bnpl_plan_id);

create table bnpl_installments (
    id uuid primary key default gen_random_uuid(),
    plan_id uuid not null references bnpl_plans(id) on delete cascade,
    seq int not null,
    due_date date not null,
    amount numeric(12,2) not null,
    is_paid boolean not null default false,
    paid_date date,
    unique (plan_id, seq)
);

create table risk_checks (
    id uuid primary key default gen_random_uuid(),
    input jsonb not null,
    feature_vector jsonb not null,
    risk_probability numeric(6,5) not null,
    risk_score int not null,
    label text not null check (label in ('safe', 'caution', 'at_risk')),
    top_factors jsonb not null,
    recommendation text not null,
    created_at timestamptz not null default now()
);

create table app_state (
    id int primary key check (id = 1),
    current_balance numeric(12,2) not null,
    balance_synced_at timestamptz not null default now(),
    -- employment encoding: 0=student, 1=employed, 2=self-employed, 3=unemployed (fixed by Engine 2 training)
    profile jsonb not null default '{"age": 22, "employment_status": 0}',
    -- false: current_balance changes only via Balance Sync (original design).
    -- true: every transaction create/edit/delete also moves current_balance
    -- (income adds, expense/savings deduct); Balance Sync becomes a manual
    -- correction tool rather than the only update path. See docs/ARCHITECTURE.md §4.1.
    ledger_mode boolean not null default false
);

insert into app_state (id, current_balance) values (1, 0.00)
on conflict (id) do nothing;
