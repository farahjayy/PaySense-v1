-- Migration: link a BNPL plan to the risk_checks row behind its score, so the score shown
-- on a plan always has a full, frozen SHAP breakdown available behind a "View full risk
-- report" button. Safe to run against the live, populated Supabase project: it only adds
-- two nullable columns and an index. Paste into the Supabase SQL editor and run once,
-- BEFORE restarting the backend.
--
-- risk_check_type distinguishes how the plan got its score:
--   'before_purchase' — the "Check before you buy" flow, confirmed into a plan
--   'current_state'   — computed automatically when an existing plan is added
-- on delete set null: deleting the underlying risk_checks row (should not normally happen)
-- leaves the plan without a report rather than deleting the plan.
--
-- Existing plans (created before this migration) get null in both columns — they simply
-- have no risk report until re-created; nothing is backfilled, there is no check to link.

alter table bnpl_plans
    add column if not exists risk_check_id uuid references risk_checks(id) on delete set null;
alter table bnpl_plans
    add column if not exists risk_check_type text
        check (risk_check_type in ('before_purchase', 'current_state'));

create index if not exists idx_bnpl_plans_risk_check on bnpl_plans (risk_check_id);
