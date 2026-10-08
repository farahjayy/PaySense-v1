# PaySense — UI Specification

Visual source of truth: `paysense_dashboard_mockup.html` (repo root). Light theme only, warm editorial feel — deliberately NOT a generic dark dashboard. Currency always `RM 1,234.56`. Responsive to 375px (sidebar → bottom nav or hamburger).

## 1. Design tokens (put in Tailwind config / CSS variables)

| Token | Value | Use |
|---|---|---|
| bg-page | `#F4F3EF` | app background |
| surface | `#FFFFFF` | cards |
| border | `#E3E1D9` | card borders, dividers |
| text-primary | `#1C1C1A` | headings, numbers |
| text-secondary | `#6B6A63` | labels |
| text-muted | `#9A988F` | captions, timestamps |
| accent | `#185FA5` / bg `#E6F1FB` | CTAs, links, active nav, income bars |
| success | `#3B6D11` / bg `#EAF3DE` | Safe label, paid badges |
| warning | `#854F0B` / bg `#FAEEDA` | Caution label, due-soon |
| danger | `#A32D2D` / bg `#FCEBEB` | At Risk, overdue, insufficient-balance alerts |
| chart extras | `#85B7EB` (projected/light blue), `#E24B4A` (expense red) | bars/lines |

Font: system stack (as mockup). Cards: white surface, 1px border, ~12px radius, generous padding; subtle shadow only where hierarchy needs it. Hover/focus states on everything interactive (accent ring on focus, slight bg shift on hover).

## 2. Layout shell

Persistent sidebar (desktop) / collapsible nav (mobile): PaySense wordmark, nav items — Dashboard, Transactions, BNPL Plans, Risk Checker — with active state (accent bg pill). Content area max-width ~1200px.

## 3. Screens

### 3.1 Dashboard (`/`)
Grid (desktop 12-col, mobile stacked):
1. **Balance card** — "Current Balance", large `RM x,xxx.xx`, "synced {relative time}", small "Sync" button → inline edit → `PUT /api/balance`.
2. **Income / Expense mini-cards** — current month totals, small trend caption.
3. **Financial Health Speedometer** — semicircular gauge 0–100 (Recharts RadialBar or custom SVG arc), needle/value + colour-coded label chip (Safe/Caution/At Risk), caption "Powered by Random Forest + your forecast". If `health_source:"rules"`, subtle "estimate" badge.
4. **6-Month Chart** — grouped bars income vs expenses per month; 3 historical solid, 3 forecast visually distinct (translucent + dashed border or hatch); legend + "AI forecast" annotation; tooltip with exact RM.
5. **BNPL plans stat card** — headline only, no per-plan list (that duplicated the Plans page; moved there 2026-09-27). Shows plan count ("N plans", deliberately not "active" since some may be overdue), then either "RM x overdue" (danger colour) + "RM y remaining", or "All caught up · RM y remaining" when nothing is overdue; "Manage →" link to `/plans`.
6. **Upcoming payment alerts** — warning-bg cards for instalments due ≤7 days; danger-bg + "balance may be insufficient" when flagged by the API.
7. **Check New BNPL** — prominent accent CTA button → `/risk-checker`.

### 3.2 Transactions (`/transactions`)
1. Toolbar: month picker, category select, type toggle (all/income/expense), search box; "Add transaction" button and "Import" split-button (CSV / PDF).
2. **Table/list** — date, description, category chip, account, amount (income green +, expense red −), BNPL badge; edit/delete row actions; pagination.
3. **Category breakdown panel** — horizontal percentage bars per category for the selected month (`/transactions/summary`).
4. **Add/Edit modal** — validated form (amount > 0, date required, type, category select, description, account, BNPL toggle).
5. **Import flow** (modal or route): dropzone → uploading state → **preview table** (editable category/type per row, issues highlighted, skipped rows listed with reasons) → "Import n transactions" → success toast → list refresh. PDF parse failure shows the friendly 422 message with a "try CSV instead" hint.

### 3.3 BNPL Plans (`/plans`)
0. **View switcher** — "By plan" (default) / "By month", styled as a distinct segmented control above the status tabs, not another filter tab.
1. **By plan**: status filter tabs (Active / Completed / Overdue / All); hidden while By month is selected (they filter plans, not months).
2. **Plan cards** — item, provider, `RM x.xx × n`, progress bar (paid/total), next due, status chip, risk-score-at-creation badge (colour-coded) when present.
3. **Create plan** — form with live preview: as the user types price/instalments/fee/date, show the schedule summary (number of instalments, per-month amount, last instalment when different — worded "N × RM x, then RM y" — total, and a "Paid at checkout" line when > 0) plus the dated list before saving.
4. **Plan detail** (`/plans/[id]`) — header with status + risk badge, Rename button (name only, any time) and Delete button (see §"Deleting a plan..." / §"Renaming a plan" below); vertical instalment timeline (seq, due date, amount, paid ✓ / due / overdue !), "Mark paid" per unpaid instalment (confirm dialog: subtracts from balance and logs an expense); plan totals (price, fee per month, total payable, per instalment).
5. **By month**: the My bills list — one row per month with instalments due (current first, then past backward, then upcoming forward; no row for an empty month), each showing the month, the comma-separated item names, the month's full total due, and a status chip (Paid / Overdue / Not paid yet); tap a row to expand the individual instalments with their own amount and paid/unpaid state. The current month's row is lightly highlighted, not structurally different from the rest. This is the same list the Dashboard showed until 2026-09-27; it now lives only here.

### 3.4 BNPL Risk Checker (`/risk-checker`) — the hero flow
1. **Input form** — item name, total price (RM), provider select (SPayLater, TikTok PayLater, Atome, Other), instalments (1–36), purchase date, first payment date (estimate auto-filled from the provider's rule, editable), fee % per month; live "≈ RM x.xx / month" preview; submit "Check my risk".
2. **Loading state** — staged messages: "Forecasting your cash flow…" → "Scoring your risk…" (matches the real sequential pipeline; ~2–5s).
3. **Result view**:
   - **Score hero** — big number + gauge fragment + label chip, `risk_probability` as small caption ("model confidence").
   - **Recommendation banner** — success/warning/danger bg matching label.
   - **Balance impact chart** — Recharts line/area: `without_purchase` (accent) vs `with_purchase` (danger) weekly curves; shaded zone below RM0; dots + tooltips on `low_balance_dates`.
   - **"Why?" panel** — top-3 SHAP factors as plain-language rows with severity dots; footer "Explained by SHAP (XAI)".
   - **Proposed schedule** — compact table of instalment dates/amounts.
   - **Actions** — "Confirm & Save to Plans" (accent; POST /risk/confirm → success → link to plan) and "Discard".
4. Errors (e.g. insufficient data) render as an in-card message with guidance ("add at least 3 months of transactions"), never a blank screen.

## 4. Component inventory (build in `components/ui/` first)

Button (primary/secondary/danger), Card, StatCard, Chip/Badge, Modal, Toast, Skeleton, EmptyState (icon + message + CTA), Gauge, CurrencyInput, DatePicker (native input ok), Select, FileDropzone, DataTable (simple), ProgressBar, Timeline.

## 5. States checklist (every screen)

- [ ] Skeleton loaders on fetch
- [ ] Empty states with a helpful CTA (e.g. no transactions → "Add your first transaction or import a statement")
- [ ] Error banners with retry
- [ ] Mobile layout at 375px without horizontal scroll

## Date format

All dates display as dd/mm/yyyy (chart axes dd/mm); the API and state use ISO yyyy-mm-dd. Date inputs are masked dd/mm/yyyy text fields with a calendar button.

## Deleting a plan with paid instalments

"Delete plan" on a plan with any paid instalment opens a dialog that lists the transactions those payments logged (count, total, first few rows) and asks: **Keep these transactions** (default; for real payments) or **Also delete them** (for a mistake or test plan). Cancel, the backdrop and Escape all cancel; nothing is deleted unless the user picks the second option and confirms. A plan with no paid instalments keeps the simple confirm.

## Renaming a plan

Plan detail has a **Rename** button (small modal, Enter saves). The item name is the only editable field, at any time, with no effect on amounts, dates or the balance; the plan's linked transactions are renamed to match. To change the price, fee, instalments or dates, delete the plan and create a new one.
