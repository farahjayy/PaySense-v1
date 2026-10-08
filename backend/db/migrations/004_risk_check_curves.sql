-- Migration: persist the balance-impact curves (without/with) alongside a risk check, so the
-- frozen risk report (docs/KNOWN_LIMITATIONS.md "Risk report...") can show the balance chart
-- too, without ever recomputing it against today's data. Safe to run against the live,
-- populated Supabase project: it only adds a nullable column. Paste into the Supabase SQL
-- editor and run once, before restarting the backend.
--
-- Existing risk_checks rows get null here — no balance chart on old reports, nothing to
-- recompute or backfill for them.

alter table risk_checks add column if not exists curves jsonb;
