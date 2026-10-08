// Currency + date helpers. Currency is always "RM 1,234.56".

const RM = new Intl.NumberFormat("en-MY", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function formatRM(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "RM 0.00";
  const sign = value < 0 ? "-" : "";
  return `${sign}RM ${RM.format(Math.abs(value))}`;
}

// Dates are shown as dd/mm/yyyy everywhere; the API and state keep ISO yyyy-mm-dd.

/** ISO yyyy-mm-dd -> dd/mm/yyyy, or "" when it is not an ISO date. */
export function isoToDisplay(iso: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  return match ? `${match[3]}/${match[2]}/${match[1]}` : "";
}

/** dd/mm/yyyy -> ISO yyyy-mm-dd, or "" when the text is not a real calendar date. */
export function displayToIso(text: string): string {
  const match = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(text);
  if (!match) return "";
  const day = Number(match[1]);
  const month = Number(match[2]);
  const year = Number(match[3]);
  const check = new Date(year, month - 1, day);
  const isReal = check.getFullYear() === year && check.getMonth() === month - 1 && check.getDate() === day;
  return isReal ? `${match[3]}-${match[2]}-${match[1]}` : "";
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return isoToDisplay(iso.slice(0, 10)) || "—";
}

export function formatMonth(yyyyMm: string): string {
  const date = new Date(`${yyyyMm}-01T00:00:00`);
  if (Number.isNaN(date.getTime())) return yyyyMm;
  return date.toLocaleDateString("en-MY", { month: "short", year: "2-digit" });
}

/** dd/mm (chart axes and tooltips). */
export function formatShortDate(iso: string): string {
  const full = isoToDisplay(iso.slice(0, 10));
  return full ? full.slice(0, 5) : iso;
}

export function relativeTime(iso: string | null | undefined): string {
  if (!iso) return "never";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "never";
  const minutes = Math.round((Date.now() - then) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return days === 1 ? "yesterday" : `${days} days ago`;
}

export function currentMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

export function todayISO(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(
    now.getDate(),
  ).padStart(2, "0")}`;
}

export function formatMonthFull(yyyyMm: string): string {
  const date = new Date(`${yyyyMm}-01T00:00:00`);
  if (Number.isNaN(date.getTime())) return yyyyMm;
  return date.toLocaleDateString("en-MY", { month: "short", year: "numeric" });
}
