// API response/request shapes — mirrors docs/API_SPEC.md.
import type { RiskLabel } from "./constants";

export type TransactionType = "income" | "expense" | "savings";

export interface Transaction {
  id: string;
  date: string;
  amount: number;
  type: TransactionType;
  category: string;
  description: string | null;
  account_name: string | null;
  is_bnpl: boolean;
  bnpl_plan_id?: string | null; // set when logged by marking a plan's instalment paid
  source: "manual" | "csv" | "pdf" | "seed";
  created_at: string;
}

export interface TransactionList {
  items: Transaction[];
  total: number;
}

export interface TransactionInput {
  date: string;
  amount: number;
  type: TransactionType;
  category: string;
  description?: string | null;
  account_name?: string | null;
  is_bnpl?: boolean;
}

export interface CategoryBreakdown {
  category: string;
  total: number;
  pct: number;
}

export interface MonthSummary {
  income: number;
  expenses: number;
  by_category: CategoryBreakdown[];
}

export interface Balance {
  current_balance: number;
  balance_synced_at: string;
}

export interface Profile {
  age: number;
  employment_status: number;
}

export interface Installment {
  id: string;
  plan_id: string;
  seq: number;
  due_date: string;
  amount: number;
  is_paid: boolean;
  paid_date: string | null;
}

export interface Plan {
  id: string;
  item_name: string;
  provider: string;
  total_price: number;
  interest_rate: number;
  num_installments: number;
  first_payment_date: string;
  status: "active" | "completed" | "overdue";
  risk_score_at_creation: number | null;
  risk_check_id: string | null;
  risk_check_type: "before_purchase" | "current_state" | null;
  created_at: string;
  installment_amount: number;
  total_payable: number; // sum of the plan's real instalments (computed by the API)
  paid_count: number;
  remaining_count: number;
  next_due_date: string | null;
  installments?: Installment[];
}

export interface PlanUpdateInput {
  item_name: string; // the only editable plan field
}

export interface PlanTransactions {
  count: number;
  total: number;
  items: { id: string; date: string; amount: number; description: string }[];
}

export interface DeletePlanResult {
  deleted_transactions: number;
  failed_transactions: number;
}

export interface PlanInput {
  item_name: string;
  provider: string;
  total_price: number;
  interest_rate: number;
  num_installments: number;
  purchase_date: string;
  first_payment_date?: string; // only sent when the user overrides the provider's default
}

export interface ChartMonth {
  month: string;
  income: number;
  expenses: number;
  is_forecast: boolean;
}

export interface DashboardAlert {
  plan_id: string;
  item_name: string;
  amount: number;
  due_date: string;
  projected_balance_sufficient: boolean;
}

export interface DashboardPlan {
  id: string;
  item_name: string;
  provider: string;
  status: string;
  installment_amount: number;
  remaining_total: number;
  paid_count: number;
  num_installments: number;
  remaining_installments: number;
  next_due_date: string | null;
}

export interface BillItem {
  plan_id: string;
  item_name: string;
  provider: string;
  seq: number;
  amount: number;
  due_date: string;
  is_paid: boolean;
}

export interface MonthlyBill {
  month: string;
  is_current: boolean;
  total_due: number;
  paid_total: number;
  fully_paid: boolean;
  has_overdue: boolean;
  items: BillItem[];
}

export interface Bills {
  months: MonthlyBill[];
}

export interface Health {
  score: number;
  label: RiskLabel;
  health_source?: "model" | "rules";
}

export interface Dashboard {
  current_balance: number;
  balance_synced_at: string;
  month_summary: { income: number; expenses: number; month: string };
  health: Health;
  chart: ChartMonth[];
  forecast_method: "arima" | "fallback_ma";
  active_plans: DashboardPlan[];
  bnpl_summary: { plan_count: number; overdue_total: number; upcoming_total: number };
  alerts: DashboardAlert[];
}

export interface CurvePoint {
  date: string;
  balance: number;
}

export interface Forecast {
  method: "arima" | "fallback_ma";
  monthly: { month: string; income: number; expenses: number; net: number }[];
  balance_curve: CurvePoint[];
  low_balance_dates: CurvePoint[];
}

export interface RiskFactor {
  feature: string;
  shap_value: number;
  message: string;
}

export interface RiskCheckInput {
  item_name: string;
  total_price: number;
  provider: string;
  num_installments: number;
  purchase_date: string;
  first_payment_date?: string; // only sent when the user overrides the provider's default
  interest_rate: number; // monthly fee, % per month
}

export interface ScheduleItem {
  seq: number;
  due_date: string;
  amount: number;
  paid_at_checkout?: boolean;
}

// One instalment as it stood at the moment a risk check ran — for annotating the balance
// chart with "instalment X of Y" style labels. Always unpaid at check time, by construction.
export interface ChartScheduleItem {
  seq: number;
  num_installments: number;
  due_date: string;
  amount: number;
  // True only for a before_purchase check's checkout-paid instalment (e.g. Atome's first) —
  // money left the account at the moment of purchase, not on a future date the chart's
  // weekly resolution would otherwise imply. current_state schedules never set this: a
  // checkout-paid instalment is already marked paid and excluded before this is built.
  paid_at_checkout: boolean;
}

export interface Curves {
  without_purchase: CurvePoint[];
  with_purchase: CurvePoint[];
  schedule: ChartScheduleItem[];
}

export interface RiskCheckResult {
  check_id: string;
  risk_probability: number;
  score: number;
  label: RiskLabel;
  top_factors: RiskFactor[];
  recommendation: string;
  curves: Curves;
  proposed_schedule: ScheduleItem[];
}

export interface ImportRow {
  row: number;
  date: string;
  amount: number;
  type: TransactionType;
  category_guess: string;
  description: string | null;
  issues: string[];
}

export interface ImportPreview {
  import_id: string;
  rows: ImportRow[];
  skipped: { row: number; reason: string }[];
}

export interface RiskReport {
  check_id: string;
  checked_at: string;
  check_type: "before_purchase" | "current_state" | null;
  risk_probability: number;
  score: number;
  label: RiskLabel;
  top_factors: RiskFactor[];
  recommendation: string;
  curves: Curves | null;
}
