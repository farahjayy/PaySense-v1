// Mirrors backend/app/constants.py — single source of domain thresholds.

export const HEALTH_SAFE_MIN = 70;
export const HEALTH_CAUTION_MIN = 40;
export const LOW_BALANCE_THRESHOLD_RM = 50;
export const ALERT_WINDOW_DAYS = 7;
export const FORECAST_MONTHS = 3;
export const MAX_INSTALLMENTS = 36;
export const MAX_INTEREST_RATE = 30;

export const TRANSACTION_CATEGORIES = [
  "Food",
  "Transport",
  "Rent",
  "Salary",
  "Allowance",
  "Shopping",
  "Bills",
  "Entertainment",
  "Education",
  "Saving",
  "Other",
] as const;

// Provider rules (start date, checkout share, billing options) live in lib/providers.ts.
export { BNPL_PROVIDERS } from "@/lib/providers";

export type RiskLabel = "safe" | "caution" | "at_risk";

export const LABEL_TEXT: Record<RiskLabel, string> = {
  safe: "Safe",
  caution: "Caution",
  at_risk: "At Risk",
};
