"use client";
// Dashboard — one aggregate API call powers everything on this screen.
// BNPL detail lives on the Plans page (by-plan cards, by-month bills); this page shows only a
// headline stat plus the 7-day alerts, so nothing is duplicated between the two.
import Link from "next/link";

import { BalanceCard } from "@/components/dashboard/BalanceCard";
import { SixMonthChart } from "@/components/dashboard/SixMonthChart";
import { Button } from "@/components/ui/Button";
import { Card, CardCaption, CardTitle } from "@/components/ui/Card";
import { Chip, labelTone } from "@/components/ui/Chip";
import { Gauge } from "@/components/ui/Gauge";
import { CardSkeleton, EmptyState, ErrorBanner } from "@/components/ui/States";
import { api } from "@/lib/api";
import { LABEL_TEXT } from "@/lib/constants";
import { formatDate, formatRM, isoToPretty, todayISO } from "@/lib/format";
import type { Dashboard } from "@/lib/types";
import { useApi } from "@/lib/useApi";

export default function DashboardPage() {
  const { data, isLoading, error, refetch } = useApi<Dashboard>(() => api.dashboard());


  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-ink">Financial health dashboard</h1>
          <p className="text-[13px] text-ink-secondary">
            {new Date().toLocaleDateString("en-MY", { weekday: "long" })}, {isoToPretty(todayISO())}
          </p>
        </div>
        <Link href="/risk-checker">
          <Button variant="accent">Check New BNPL Purchase →</Button>
        </Link>
      </header>

      {error && <ErrorBanner message={error} onRetry={refetch} />}

      {isLoading && (
        <div className="grid gap-4 md:grid-cols-3">
          <CardSkeleton lines={2} />
          <CardSkeleton lines={2} />
          <CardSkeleton lines={2} />
          <div className="md:col-span-3">
            <CardSkeleton lines={6} />
          </div>
        </div>
      )}

      {data && !isLoading && (
        <>
          <div className="grid gap-4 md:grid-cols-3">
            <BalanceCard
              balance={data.current_balance}
              syncedAt={data.balance_synced_at}
              onSynced={refetch}
            />
            <div className="grid grid-cols-2 gap-4 md:col-span-1">
              <Card>
                <p className="text-xs font-medium text-ink-secondary">Income this month</p>
                <p className="mt-1 text-xl font-bold text-success">
                  {formatRM(data.month_summary.income)}
                </p>
                <p className="mt-1 text-[11px] text-ink-muted">{data.month_summary.month}</p>
              </Card>
              <Card>
                <p className="text-xs font-medium text-ink-secondary">Spent this month</p>
                <p className="mt-1 text-xl font-bold text-chart-red">
                  {formatRM(data.month_summary.expenses)}
                </p>
                <p className="mt-1 text-[11px] text-ink-muted">{data.month_summary.month}</p>
              </Card>
            </div>
            <Card className="flex flex-col items-center text-center">
              <div className="flex w-full items-center justify-center gap-2">
                <p className="text-[13px] font-bold text-ink">Financial health score</p>
                {data.health.health_source === "rules" && <Chip tone="neutral">estimate</Chip>}
              </div>
              <Gauge score={data.health.score} size={170} />
              <p className="-mt-1 text-3xl font-bold">
                {data.health.score}
                <span className="text-sm font-normal text-ink-secondary">/100</span>
              </p>
              <div className="mt-1.5">
                <Chip tone={labelTone(data.health.label)}>{LABEL_TEXT[data.health.label]}</Chip>
              </div>
              <p className="mt-2 max-w-[230px] text-[11px] text-ink-muted">
                Powered by Random Forest + your cash-flow forecast
              </p>
            </Card>
          </div>

          <Card>
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <div>
                <CardTitle>6-month cash flow</CardTitle>
                <CardCaption>
                  3 months of history + 3 months of AI forecast (
                  {data.forecast_method === "arima" ? "ARIMA" : "moving average"})
                </CardCaption>
              </div>
              <Chip tone="accent">AI forecast →</Chip>
            </div>
            <div className="mt-3">
              {data.chart.length > 0 ? (
                <SixMonthChart data={data.chart} />
              ) : (
                <EmptyState
                  icon="📊"
                  message="No transaction history yet — add transactions or import a statement to unlock forecasting."
                />
              )}
            </div>
          </Card>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="flex flex-col justify-center gap-2">
              <CardTitle>BNPL plans</CardTitle>
              {data.bnpl_summary.plan_count === 0 ? (
                <>
                  <p className="text-[13px] text-ink-secondary">No BNPL plans.</p>
                  <Link href="/risk-checker" className="text-xs font-semibold text-accent hover:underline">
                    Check a purchase →
                  </Link>
                </>
              ) : (
                <>
                  <p className="text-2xl font-bold text-ink">
                    {data.bnpl_summary.plan_count} {data.bnpl_summary.plan_count === 1 ? "plan" : "plans"}
                  </p>
                  {data.bnpl_summary.overdue_total > 0 ? (
                    <>
                      <p className="text-[13px] font-semibold text-danger">
                        {formatRM(data.bnpl_summary.overdue_total)} overdue
                      </p>
                      <p className="text-[12px] text-ink-secondary">
                        {formatRM(data.bnpl_summary.upcoming_total)} remaining
                      </p>
                    </>
                  ) : (
                    <p className="text-[13px] text-ink-secondary">
                      All caught up · {formatRM(data.bnpl_summary.upcoming_total)} remaining
                    </p>
                  )}
                  <Link href="/plans" className="text-xs font-semibold text-accent hover:underline">
                    Manage →
                  </Link>
                </>
              )}
            </Card>

            <Card>
              <CardTitle>Upcoming payment alerts</CardTitle>
              <CardCaption>Instalments due within 7 days</CardCaption>
              <div className="mt-3 flex flex-col gap-2">
                {data.alerts.length === 0 && (
                  <EmptyState icon="✅" message="Nothing due in the next 7 days — you're clear." />
                )}
                {data.alerts.map((alert) => (
                  <div
                    key={`${alert.plan_id}-${alert.due_date}`}
                    className={`rounded-lg border px-3.5 py-2.5 ${
                      alert.projected_balance_sufficient
                        ? "border-warning/30 bg-warning-bg"
                        : "border-danger/30 bg-danger-bg"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p
                        className={`text-[13px] font-semibold ${
                          alert.projected_balance_sufficient ? "text-warning" : "text-danger"
                        }`}
                      >
                        {alert.item_name} — {formatRM(alert.amount)}
                      </p>
                      <p className="text-[11px] font-medium text-ink-secondary">
                        {formatDate(alert.due_date)}
                      </p>
                    </div>
                    {!alert.projected_balance_sufficient && (
                      <p className="mt-0.5 text-[11px] font-medium text-danger">
                        ⚠ Your projected balance may be insufficient for this payment
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
