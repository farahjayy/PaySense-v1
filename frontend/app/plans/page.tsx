"use client";
// BNPL Plans: a view switcher (By plan / By month) above the plan list.
// By plan (default): the existing status tabs + card grid, unchanged.
// By month: the "My bills" monthly ledger, which owns this content now — the Dashboard no
// longer duplicates it. The status tabs only make sense for By plan, so they hide in By month.
import Link from "next/link";
import { useState } from "react";

import { MonthlyBillsCard } from "@/components/dashboard/MonthlyBillsCard";
import { CreatePlanModal } from "@/components/plans/CreatePlanModal";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Chip, statusTone } from "@/components/ui/Chip";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { CardSkeleton, EmptyState, ErrorBanner } from "@/components/ui/States";
import { api } from "@/lib/api";
import { HEALTH_CAUTION_MIN, HEALTH_SAFE_MIN } from "@/lib/constants";
import { formatDate, formatRM } from "@/lib/format";
import type { Bills, Plan } from "@/lib/types";
import { useApi } from "@/lib/useApi";

const STATUS_TABS = [
  ["", "All"],
  ["active", "Active"],
  ["completed", "Completed"],
  ["overdue", "Overdue"],
] as const;

const VIEW_MODES = [
  ["byPlan", "📋", "By plan"],
  ["byMonth", "📅", "By month"],
] as const;

type ViewMode = (typeof VIEW_MODES)[number][0];

function riskBadgeTone(score: number) {
  if (score >= HEALTH_SAFE_MIN) return "success" as const;
  if (score >= HEALTH_CAUTION_MIN) return "warning" as const;
  return "danger" as const;
}

function ViewSwitcher({ value, onChange }: { value: ViewMode; onChange: (mode: ViewMode) => void }) {
  return (
    <div className="flex w-fit gap-1 rounded-xl border border-line bg-surface-2 p-1" role="tablist" aria-label="View">
      {VIEW_MODES.map(([mode, icon, label]) => (
        <button
          key={mode}
          type="button"
          role="tab"
          aria-selected={value === mode}
          onClick={() => onChange(mode)}
          className={`rounded-lg px-4 py-2 text-[13px] font-semibold transition-colors ${
            value === mode ? "bg-ink text-white shadow-sm" : "text-ink-secondary hover:text-ink"
          }`}
        >
          {icon} {label}
        </button>
      ))}
    </div>
  );
}

function ByPlanView() {
  const [statusFilter, setStatusFilter] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const { data, isLoading, error, refetch } = useApi<Plan[]>(
    () => api.plans(statusFilter || undefined),
    [statusFilter],
  );

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div
          className="flex w-fit overflow-hidden rounded-lg border border-line"
          role="tablist"
          aria-label="Status filter"
        >
          {STATUS_TABS.map(([value, label]) => (
            <button
              key={value}
              type="button"
              role="tab"
              aria-selected={statusFilter === value}
              onClick={() => setStatusFilter(value)}
              className={`h-9 px-4 text-[13px] font-medium transition-colors ${
                statusFilter === value
                  ? "bg-accent-bg font-semibold text-accent"
                  : "bg-surface text-ink-secondary hover:bg-surface-2"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <Button variant="secondary" onClick={() => setIsCreating(true)}>
          + Add existing plan
        </Button>
      </div>

      {error && <ErrorBanner message={error} onRetry={refetch} />}
      {isLoading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <CardSkeleton lines={4} />
          <CardSkeleton lines={4} />
          <CardSkeleton lines={4} />
        </div>
      )}

      {data && !isLoading && data.length === 0 && (
        <EmptyState
          icon="🛍️"
          message={
            statusFilter
              ? `No ${statusFilter} plans.`
              : "No BNPL plans yet — run a purchase through the Risk Checker first, or add an existing plan."
          }
          action={
            <Link href="/risk-checker">
              <Button size="sm" variant="accent">Open Risk Checker</Button>
            </Link>
          }
        />
      )}

      {data && !isLoading && data.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.map((plan) => (
            <Link key={plan.id} href={`/plans/${plan.id}`} className="group">
              <Card className="flex h-full flex-col gap-3 transition-shadow group-hover:shadow-md">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-ink">{plan.item_name}</p>
                    <p className="text-[11px] text-ink-muted">{plan.provider}</p>
                  </div>
                  <Chip tone={statusTone(plan.status)}>{plan.status}</Chip>
                </div>
                <p className="text-lg font-bold text-ink">
                  {formatRM(plan.installment_amount)}
                  <span className="text-xs font-normal text-ink-secondary">
                    {" "}
                    × {plan.num_installments}
                  </span>
                </p>
                <div>
                  <ProgressBar value={plan.paid_count} max={plan.num_installments} />
                  <p className="mt-1 text-[11px] text-ink-muted">
                    {plan.paid_count} of {plan.num_installments} paid
                    {plan.next_due_date && ` · next due ${formatDate(plan.next_due_date)}`}
                  </p>
                </div>
                {plan.risk_score_at_creation !== null && (
                  <div className="mt-auto">
                    <Chip tone={riskBadgeTone(plan.risk_score_at_creation)}>
                      Risk-checked · {plan.risk_score_at_creation}/100
                    </Chip>
                  </div>
                )}
              </Card>
            </Link>
          ))}
        </div>
      )}

      <CreatePlanModal isOpen={isCreating} onClose={() => setIsCreating(false)} onCreated={refetch} />
    </div>
  );
}

function ByMonthView() {
  const { data, isLoading, error, refetch } = useApi<Bills>(() => api.bills());

  if (error) return <ErrorBanner message={error} onRetry={refetch} />;
  if (isLoading) return <CardSkeleton lines={6} />;
  return <MonthlyBillsCard months={data?.months ?? []} />;
}

export default function PlansPage() {
  const [viewMode, setViewMode] = useState<ViewMode>("byPlan");

  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-ink">BNPL Plans</h1>
          <p className="text-[13px] text-ink-secondary">Track every instalment commitment</p>
        </div>
        <Link href="/risk-checker">
          <Button variant="accent">Check before you buy →</Button>
        </Link>
      </header>

      <ViewSwitcher value={viewMode} onChange={setViewMode} />

      {viewMode === "byPlan" ? <ByPlanView /> : <ByMonthView />}
    </div>
  );
}
