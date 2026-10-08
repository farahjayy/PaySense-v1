// Mirrors backend/app/providers.py — BNPL provider rules as data. Adding a provider means
// adding one PROVIDERS entry (in both files). The backend is the authority when a plan is
// created; this copy only drives live previews. Source: docs/BNPL Billing Rules ... .md.
//
// checkoutInstalments: leading instalments charged at checkout (Atome: 1 = one-third of a
//   3-payment plan). startRule: purchase_date | months_after_purchase (later instalments
//   repeat the first date's day-of-month). monthlyFeeApplies: false forces the fee to 0.

export type StartRule = "purchase_date" | "months_after_purchase";

export interface ProviderConfig {
  name: string;
  checkoutInstalments: number;
  startRule: StartRule;
  startOffsetMonths: number;
  monthlyFeeApplies: boolean;
}

const DEFAULTS = {
  checkoutInstalments: 0,
  startRule: "purchase_date" as StartRule,
  startOffsetMonths: 0,
  monthlyFeeApplies: true,
};

export const PROVIDERS: Record<string, ProviderConfig> = {
  SPayLater: { ...DEFAULTS, name: "SPayLater", startRule: "months_after_purchase", startOffsetMonths: 1 },
  "TikTok PayLater": {
    ...DEFAULTS,
    name: "TikTok PayLater",
    startRule: "months_after_purchase",
    startOffsetMonths: 1,
  },
  Atome: { ...DEFAULTS, name: "Atome", checkoutInstalments: 1 },
  Other: { ...DEFAULTS, name: "Other" },
};

const FALLBACK_PROVIDER = "Other";

/** Config for `name`; unknown or retired providers behave as Other. */
export function getProvider(name: string): ProviderConfig {
  return PROVIDERS[name] ?? PROVIDERS[FALLBACK_PROVIDER];
}

export const BNPL_PROVIDERS: string[] = Object.keys(PROVIDERS);
