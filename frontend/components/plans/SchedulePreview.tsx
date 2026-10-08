"use client";
// Headline numbers for the instalment schedule being entered: how many instalments, the
// per-month amount, the last instalment when the leftover sen make it differ, the total, and
// what is charged at checkout (Atome).
import { formatRM } from "@/lib/format";
import { summarizeSchedule, type PreviewInstallment } from "@/lib/schedule";

type Props = {
  schedule: PreviewInstallment[];
};

export function SchedulePreview({ schedule }: Props) {
  const summary = summarizeSchedule(schedule);
  if (!summary) return null;

  return (
    <div className="flex flex-col gap-0.5 text-[13px]">
      <p className="font-medium text-ink">
        {summary.hasDifferentLast ? (
          <>
            {summary.count - 1} × {formatRM(summary.perMonth)}, then {formatRM(summary.last)}
          </>
        ) : (
          <>
            {summary.count} {summary.count === 1 ? "instalment" : "instalments"} of {formatRM(summary.perMonth)}{" "}
            each
          </>
        )}
      </p>
      <p className="text-ink-secondary">Total {formatRM(summary.total)}</p>
      {summary.paidAtCheckout > 0 && (
        <p className="font-medium text-success">Paid at checkout: {formatRM(summary.paidAtCheckout)}</p>
      )}
    </div>
  );
}
