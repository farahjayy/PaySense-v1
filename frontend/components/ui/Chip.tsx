import type { ReactNode } from "react";

import type { RiskLabel } from "@/lib/constants";

export type ChipTone = "success" | "warning" | "danger" | "accent" | "neutral";

const TONE_CLASSES: Record<ChipTone, string> = {
  success: "bg-success-bg text-success",
  warning: "bg-warning-bg text-warning",
  danger: "bg-danger-bg text-danger",
  accent: "bg-accent-bg text-accent",
  neutral: "bg-surface-2 text-ink-secondary border border-line",
};

export function Chip({ tone = "neutral", children }: { tone?: ChipTone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center whitespace-nowrap rounded-md px-2.5 py-1 text-[11px] font-semibold ${TONE_CLASSES[tone]}`}
    >
      {children}
    </span>
  );
}

export function labelTone(label: RiskLabel): ChipTone {
  if (label === "safe") return "success";
  if (label === "caution") return "warning";
  return "danger";
}

export function statusTone(status: string): ChipTone {
  if (status === "completed") return "success";
  if (status === "overdue") return "danger";
  return "accent";
}
