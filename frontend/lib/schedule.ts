// Mirror of backend/app/services/schedule.py — used only for live previews;
// the backend remains the authority when a plan is actually created.
//
// All money maths is in integer sen. The fee is a MONTHLY rate:
// total = price x (1 + monthlyRate/100 x instalments), rounded half up to the sen; each
// instalment is total / count rounded DOWN to the sen; leftover sen go in the LAST one.

import { getProvider } from "@/lib/providers";

export interface PreviewInstallment {
  seq: number;
  dueDate: string;
  amount: number;
  paidAtCheckout: boolean;
}

export interface ScheduleSummary {
  count: number;
  perMonth: number;
  last: number;
  hasDifferentLast: boolean;
  total: number;
  paidAtCheckout: number;
}

const RATE_SCALE = 10_000;

/** RM -> integer sen. The toPrecision step removes float noise (147.62 * 100 = 14762.000000000002). */
export function toSen(rm: number): number {
  return Math.round(parseFloat((rm * 100).toPrecision(12)));
}

export function fromSen(sen: number): number {
  return sen / 100;
}

function totalPayableSen(priceSen: number, monthlyRate: number, numInstallments: number): number {
  const rateHundredths = Math.round(parseFloat((monthlyRate * 100).toPrecision(12)));
  const numerator = priceSen * (RATE_SCALE + rateHundredths * numInstallments);
  return Math.floor((numerator + RATE_SCALE / 2) / RATE_SCALE);
}

/** Price plus the monthly fee for every instalment month, to the nearest sen. */
export function totalPayable(price: number, monthlyRate: number, numInstallments: number): number {
  return fromSen(totalPayableSen(toSen(price), monthlyRate, numInstallments));
}

function splitSen(totalSen: number, numInstallments: number): number[] {
  const base = Math.floor(totalSen / numInstallments);
  return [...Array(numInstallments - 1).fill(base), totalSen - base * (numInstallments - 1)];
}

function pad2(value: number): string {
  return String(value).padStart(2, "0");
}

export function addMonths(isoDate: string, months: number): string {
  const [year, month, day] = isoDate.split("-").map(Number);
  const monthIndex = month - 1 + months;
  const targetYear = year + Math.floor(monthIndex / 12);
  const targetMonth = ((monthIndex % 12) + 12) % 12;
  const lastDay = new Date(targetYear, targetMonth + 1, 0).getDate();
  const targetDay = Math.min(day, lastDay);
  return `${targetYear}-${pad2(targetMonth + 1)}-${pad2(targetDay)}`;
}

/** First due date implied by the provider's billing rule (mirrors default_first_payment_date). */
export function defaultFirstPaymentDate(provider: string, purchaseDate: string): string {
  const config = getProvider(provider);
  if (config.startRule === "months_after_purchase") return addMonths(purchaseDate, config.startOffsetMonths);
  return purchaseDate;
}

/** Number of leading instalments charged at checkout (0 unless the first due date is the purchase date). */
export function checkoutInstalments(provider: string, firstPaymentDate: string, purchaseDate: string): number {
  const config = getProvider(provider);
  return config.checkoutInstalments > 0 && firstPaymentDate === purchaseDate ? config.checkoutInstalments : 0;
}

/** Short explanation shown under the first-payment-date field. */
export function firstPaymentHint(provider: string): string {
  const config = getProvider(provider);
  if (config.startRule === "months_after_purchase") {
    return "Nothing is charged at checkout. First bill estimated one month after purchase — edit it if your app shows a different due date.";
  }
  if (config.checkoutInstalments > 0) {
    return "The first payment is charged to your card at checkout, so it counts as already paid.";
  }
  return "Set this to your provider's first due date.";
}

export function previewSchedule(
  totalPrice: number,
  monthlyRate: number,
  numInstallments: number,
  firstPaymentDate: string,
  checkoutCount = 0,
): PreviewInstallment[] {
  if (!(totalPrice > 0) || numInstallments < 1 || !firstPaymentDate) return [];
  const amounts = splitSen(totalPayableSen(toSen(totalPrice), monthlyRate, numInstallments), numInstallments);
  return amounts.map((sen, index) => ({
    seq: index + 1,
    dueDate: addMonths(firstPaymentDate, index),
    amount: fromSen(sen),
    paidAtCheckout: index + 1 <= checkoutCount,
  }));
}

/** Headline numbers for the preview: count, per-month, last (if different), total, paid at checkout. */
export function summarizeSchedule(schedule: PreviewInstallment[]): ScheduleSummary | null {
  if (schedule.length === 0) return null;
  const sen = schedule.map((item) => toSen(item.amount));
  const last = sen[sen.length - 1];
  return {
    count: schedule.length,
    perMonth: fromSen(sen[0]),
    last: fromSen(last),
    hasDifferentLast: schedule.length > 1 && last !== sen[0],
    total: fromSen(sen.reduce((sum, value) => sum + value, 0)),
    paidAtCheckout: fromSen(
      schedule.reduce((sum, item, index) => (item.paidAtCheckout ? sum + sen[index] : sum), 0),
    ),
  };
}
