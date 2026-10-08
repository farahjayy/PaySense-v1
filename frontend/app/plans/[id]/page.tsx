"use client";
// Plan detail: header + totals + vertical instalment timeline with mark-paid.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { use, useState } from "react";

import { DeletePlanDialog } from "@/components/plans/DeletePlanDialog";
import { RenamePlanModal } from "@/components/plans/RenamePlanModal";
import { Button } from "@/components/ui/Button";
import { Card, CardCaption, CardTitle } from "@/components/ui/Card";
import { Chip, statusTone } from "@/components/ui/Chip";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { CardSkeleton, ErrorBanner } from "@/components/ui/States";
import { useToast } from "@/components/ui/Toast";
import { api, ApiError } from "@/lib/api";
import { HEALTH_CAUTION_MIN, HEALTH_SAFE_MIN } from "@/lib/constants";
import { formatDate, formatRM, todayISO } from "@/lib/format";
import type { Installment, Plan } from "@/lib/types";
import { useApi } from "@/lib/useApi";

export default function PlanDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const toast = useToast();
  const [payingSeq, setPayingSeq] = useState<number | null>(null);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [isRenaming, setIsRenaming] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const { data: plan, isLoading, error, refetch } = useApi<Plan>(() => api.plan(id), [id]);

  const today = todayISO();

  const handlePay = async (installment: Installment) => {
    const confirmed = window.confirm(
      `Mark instalment #${installment.seq} (${formatRM(installment.amount)}) as paid?\n\n` +
        "This subtracts it from your balance and logs a matching expense transaction.",
    );
    if (!confirmed) return;
    setPayingSeq(installment.seq);
    try {
      await api.payInstallment(id, installment.seq);
      toast("success", `Instalment #${installment.seq} marked paid.`);
      refetch();
    } catch (err) {
      toast("error", err instanceof ApiError ? err.message : "Couldn't mark the instalment paid.");
    } finally {
      setPayingSeq(null);
    }
  };

  const deletePlan = async (deleteTransactions: boolean) => {
    setIsDeleting(true);
    try {
      const result = await api.deletePlan(id, deleteTransactions);
      if (result.failed_transactions > 0) {
        toast(
          "error",
          `Plan deleted, but ${result.failed_transactions} transaction(s) couldn't be removed — delete them from Transactions.`,
        );
      } else if (result.deleted_transactions > 0) {
        toast("success", `Plan deleted, and ${result.deleted_transactions} transaction(s) removed.`);
      } else {
        toast("success", "Plan deleted. Its transactions were kept.");
      }
      router.push("/plans");
    } catch (err) {
      toast("error", err instanceof ApiError ? err.message : "Couldn't delete the plan.");
      setIsDeleting(false);
      setIsDeleteDialogOpen(false);
    }
  };

  const handleDelete = () => {
    if (!plan) return;
    // Paid instalments may have logged transactions: ask what to do with them (default: keep).
    if (plan.paid_count > 0) {
      setIsDeleteDialogOpen(true);
      return;
    }
    if (window.confirm(`Delete the plan "${plan.item_name}" and all its instalments?`)) {
      void deletePlan(false);
    }
  };

  const riskTone =
    plan?.risk_score_at_creation == null
      ? null
      : plan.risk_score_at_creation >= HEALTH_SAFE_MIN
        ? ("success" as const)
        : plan.risk_score_at_creation >= HEALTH_CAUTION_MIN
          ? ("warning" as const)
          : ("danger" as const);

  return (
    <div className="flex flex-col gap-4">
      <Link href="/plans" className="w-fit text-xs font-semibold text-accent hover:underline">
        ← All plans
      </Link>

      {error && <ErrorBanner message={error} onRetry={refetch} />}
      {isLoading && <CardSkeleton lines={8} />}

      {plan && !isLoading && (
        <>
          <Card>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h1 className="text-lg font-semibold text-ink">{plan.item_name}</h1>
                  <Chip tone={statusTone(plan.status)}>{plan.status}</Chip>
                  {riskTone && (
                    <Chip tone={riskTone}>
                      {plan.risk_check_type === "current_state" ? "Current risk" : "Risk-checked"} ·{" "}
                      {plan.risk_score_at_creation}/100
                    </Chip>
                  )}
                </div>
                <p className="mt-0.5 text-[13px] text-ink-secondary">
                  {plan.provider} · started {formatDate(plan.first_payment_date)}
                </p>
                {plan.risk_check_id && (
                  <Link
                    href={`/plans/${plan.id}/risk-report`}
                    className="mt-1 inline-block text-xs font-semibold text-accent hover:underline"
                  >
                    View full risk report →
                  </Link>
                )}
              </div>
              <div className="flex gap-2">
                <Button variant="secondary" size="sm" onClick={() => setIsRenaming(true)}>
                  Rename
                </Button>
                <Button variant="danger" size="sm" onClick={handleDelete}>
                  Delete plan
                </Button>
              </div>
            </div>

            <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div>
                <p className="text-[11px] text-ink-muted">Price</p>
                <p className="text-sm font-semibold text-ink">{formatRM(plan.total_price)}</p>
              </div>
              <div>
                <p className="text-[11px] text-ink-muted">Fee per month</p>
                <p className="text-sm font-semibold text-ink">{plan.interest_rate}% / month</p>
              </div>
              <div>
                <p className="text-[11px] text-ink-muted">Total payable</p>
                <p className="text-sm font-semibold text-ink">{formatRM(plan.total_payable)}</p>
              </div>
              <div>
                <p className="text-[11px] text-ink-muted">Per instalment</p>
                <p className="text-sm font-semibold text-ink">{formatRM(plan.installment_amount)}</p>
              </div>
            </div>
            <div className="mt-4">
              <ProgressBar value={plan.paid_count} max={plan.num_installments} />
              <p className="mt-1 text-[11px] text-ink-muted">
                {plan.paid_count} of {plan.num_installments} instalments paid
              </p>
            </div>
          </Card>

          <Card>
            <CardTitle>Instalment timeline</CardTitle>
            <CardCaption>Marking one paid also logs an expense transaction</CardCaption>
            <ol className="mt-4 flex flex-col">
              {(plan.installments ?? []).map((installment, index) => {
                const isOverdue = !installment.is_paid && installment.due_date < today;
                const isLast = index === (plan.installments?.length ?? 0) - 1;
                return (
                  <li key={installment.seq} className="relative flex gap-3 pb-5 last:pb-0">
                    {!isLast && (
                      <span
                        aria-hidden
                        className="absolute left-[11px] top-6 h-full w-px bg-line"
                      />
                    )}
                    <span
                      aria-hidden
                      className={`z-10 mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-[11px] font-bold ${
                        installment.is_paid
                          ? "border-success bg-success-bg text-success"
                          : isOverdue
                            ? "border-danger bg-danger-bg text-danger"
                            : "border-line bg-surface-2 text-ink-muted"
                      }`}
                    >
                      {installment.is_paid ? "✓" : isOverdue ? "!" : installment.seq}
                    </span>
                    <div className="flex flex-1 flex-wrap items-center justify-between gap-2">
                      <div>
                        <p className="text-[13px] font-semibold text-ink">
                          #{installment.seq} · {formatRM(installment.amount)}
                        </p>
                        <p className="text-[11px] text-ink-muted">
                          {installment.is_paid
                            ? `Paid ${formatDate(installment.paid_date)}`
                            : isOverdue
                              ? `Overdue — was due ${formatDate(installment.due_date)}`
                              : `Due ${formatDate(installment.due_date)}`}
                        </p>
                      </div>
                      {!installment.is_paid && (
                        <Button
                          size="sm"
                          variant={isOverdue ? "danger" : "secondary"}
                          disabled={payingSeq === installment.seq}
                          onClick={() => handlePay(installment)}
                        >
                          {payingSeq === installment.seq ? "Saving…" : "Mark paid"}
                        </Button>
                      )}
                    </div>
                  </li>
                );
              })}
            </ol>
          </Card>
        </>
      )}

      {isRenaming && plan && (
        <RenamePlanModal plan={plan} onClose={() => setIsRenaming(false)} onSaved={refetch} />
      )}

      {isDeleteDialogOpen && plan && (
        <DeletePlanDialog
          plan={plan}
          isDeleting={isDeleting}
          onCancel={() => setIsDeleteDialogOpen(false)}
          onConfirm={deletePlan}
        />
      )}
    </div>
  );
}
