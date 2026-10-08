"use client";
// "My Bills": instalments due across every tracked plan, one row per month. Current month
// first, then past months going backward, then upcoming months going forward (the order the
// backend already returns them in). A month only appears if something is actually due in it —
// no synthetic RM0 row. Every row uses the same layout; the current month is only lightly
// highlighted, not structurally different. Tap a row to see its individual instalments.
import { useState } from "react";

import { Card, CardCaption, CardTitle } from "@/components/ui/Card";
import { Chip, type ChipTone } from "@/components/ui/Chip";
import { EmptyState } from "@/components/ui/States";
import { formatMonthFull, formatRM } from "@/lib/format";
import type { MonthlyBill } from "@/lib/types";

type Props = {
  months: MonthlyBill[];
};

type Status = { label: string; tone: ChipTone };

/** Paid only if every instalment due that month is paid; otherwise overdue once the due date
 * has passed, else just not paid yet. */
function status(bill: MonthlyBill): Status {
  if (bill.fully_paid) return { label: "Paid", tone: "success" };
  if (bill.has_overdue) return { label: "Overdue", tone: "danger" };
  return { label: "Not paid yet", tone: "warning" };
}

function BillRow({ bill }: { bill: MonthlyBill }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const { label, tone } = status(bill);
  const itemNames = bill.items.map((item) => item.item_name).join(", ");

  return (
    <div className={bill.is_current ? "bg-accent-bg" : undefined}>
      <button
        type="button"
        className="flex w-full items-center justify-between gap-3 px-1 py-2.5 text-left"
        onClick={() => setIsExpanded((current) => !current)}
        aria-expanded={isExpanded}
      >
        <div className="min-w-0">
          <p className="flex items-center gap-1.5 text-[13px] font-semibold text-ink">
            {formatMonthFull(bill.month)}
            {bill.is_current && <span className="text-[10px] font-medium text-accent">this month</span>}
          </p>
          <p className="truncate text-[11px] text-ink-muted">{itemNames}</p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <p className="text-[13px] font-semibold text-ink">{formatRM(bill.total_due)}</p>
          <Chip tone={tone}>{label}</Chip>
          <svg
            width="12"
            height="12"
            viewBox="0 0 12 12"
            fill="none"
            aria-hidden
            className={`text-ink-muted transition-transform ${isExpanded ? "rotate-180" : ""}`}
          >
            <path d="M2.5 4.5 6 8l3.5-3.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
          </svg>
        </div>
      </button>

      {isExpanded && (
        <ul className="flex flex-col gap-1 px-1 pb-3">
          {bill.items.map((item) => (
            <li key={`${item.plan_id}-${item.seq}`} className="flex items-center justify-between text-[12px]">
              <span className="truncate text-ink-secondary">
                {item.item_name} #{item.seq}
              </span>
              <span className={`shrink-0 font-medium ${item.is_paid ? "text-success" : "text-ink"}`}>
                {formatRM(item.amount)} · {item.is_paid ? "paid" : "unpaid"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function MonthlyBillsCard({ months }: Props) {
  return (
    <Card>
      <CardTitle>My bills</CardTitle>
      <CardCaption>Instalments due across all your BNPL plans, by month</CardCaption>

      {months.length === 0 ? (
        <div className="mt-3">
          <EmptyState icon="🧾" message="No instalments due — nothing to bill." />
        </div>
      ) : (
        <div className="mt-2 flex flex-col divide-y divide-line">
          {months.map((bill) => (
            <BillRow key={bill.month} bill={bill} />
          ))}
        </div>
      )}
    </Card>
  );
}
