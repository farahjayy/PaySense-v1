"use client";
// Full risk report for a plan: the exact SHAP breakdown that produced the score shown on the
// plan, fetched once and never recomputed. GET /api/bnpl/plans/{id}/risk-report always returns
// the frozen risk_checks row the plan was linked to (at "Check before you buy" confirm time,
// or automatically when an existing plan was added) — this page just displays it.
import Link from "next/link";
import { use } from "react";

import { OverlayChart } from "@/components/risk/OverlayChart";
import { WhyThisScore } from "@/components/risk/WhyThisScore";
import { Card, CardCaption, CardTitle } from "@/components/ui/Card";
import { Chip, labelTone } from "@/components/ui/Chip";
import { Gauge } from "@/components/ui/Gauge";
import { CardSkeleton, ErrorBanner } from "@/components/ui/States";
import { api } from "@/lib/api";
import { LABEL_TEXT } from "@/lib/constants";
import { formatDate } from "@/lib/format";
import type { RiskReport } from "@/lib/types";
import { useApi } from "@/lib/useApi";

const CHECK_TYPE_TEXT: Record<string, string> = {
  before_purchase: "Checked before this purchase was made",
  current_state: "Checked automatically when this plan was added",
};

export default function PlanRiskReportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: report, isLoading, error, refetch } = useApi<RiskReport>(() => api.planRiskReport(id), [id]);

  return (
    <div className="flex flex-col gap-4">
      <Link href={`/plans/${id}`} className="w-fit text-xs font-semibold text-accent hover:underline">
        ← Back to plan
      </Link>

      {error && <ErrorBanner message={error} onRetry={refetch} />}
      {isLoading && <CardSkeleton lines={8} />}

      {report && !isLoading && (
        <>
          <Card className="flex flex-col items-center text-center">
            <p className="text-[13px] font-bold text-ink">Risk report</p>
            <Gauge score={report.score} size={160} />
            <p className="-mt-1 text-4xl font-bold text-ink">
              {report.score}
              <span className="text-sm font-normal text-ink-secondary">/100</span>
            </p>
            <div className="mt-1.5">
              <Chip tone={labelTone(report.label)}>{LABEL_TEXT[report.label]}</Chip>
            </div>
            <p className="mt-2 text-[11px] text-ink-muted">
              P(risk) = {report.risk_probability.toFixed(2)}
            </p>
            <p className="mt-1 text-[11px] text-ink-muted">
              {report.check_type && CHECK_TYPE_TEXT[report.check_type]} · {formatDate(report.checked_at)}
            </p>
            <p className="mt-3 max-w-md text-[13px] font-medium text-ink">{report.recommendation}</p>
          </Card>

          <WhyThisScore factors={report.top_factors} />

          {report.curves && (
            <Card>
              <CardTitle>Balance impact</CardTitle>
              <CardCaption>
                Weekly projected balance from this check&apos;s forecast, frozen at the time it ran
              </CardCaption>
              <div className="mt-3">
                <OverlayChart
                  withoutPurchase={report.curves.without_purchase}
                  withPurchase={report.curves.with_purchase}
                  schedule={report.curves.schedule}
                  subject={report.check_type === "current_state" ? "plan" : "purchase"}
                />
              </div>
            </Card>
          )}

          <p className="text-[11px] text-ink-muted">
            This is a frozen snapshot from the moment the check ran — it does not update as your
            finances change. Run a new check from the Risk Checker for an up-to-date score.
          </p>
        </>
      )}
    </div>
  );
}
