"use client";
// Risk Checker — the hero flow: form → staged loading (Engine 1 → Engine 2) →
// score hero, recommendation, curve overlay, SHAP factors, schedule, confirm.
import Link from "next/link";
import { useEffect, useState } from "react";

import { SchedulePreview } from "@/components/plans/SchedulePreview";
import { OverlayChart } from "@/components/risk/OverlayChart";
import { Button } from "@/components/ui/Button";
import { Card, CardCaption, CardTitle } from "@/components/ui/Card";
import { Chip, labelTone } from "@/components/ui/Chip";
import { Gauge } from "@/components/ui/Gauge";
import { useToast } from "@/components/ui/Toast";
import { CurrencyField, DateField, SelectField, TextField } from "@/components/ui/fields";
import { api, ApiError } from "@/lib/api";
import {
  BNPL_PROVIDERS,
  LABEL_TEXT,
  MAX_INSTALLMENTS,
  MAX_INTEREST_RATE,
} from "@/lib/constants";
import { formatDate, formatRM } from "@/lib/format";
import { firstPaymentHint, previewSchedule } from "@/lib/schedule";
import type { Plan, RiskCheckResult } from "@/lib/types";
import { useScheduleInputs } from "@/lib/useScheduleInputs";

type Stage = "form" | "loading" | "result";

const LOADING_MESSAGES = [
  "Forecasting your cash flow…",
  "Scoring your risk…",
];

const BANNER_CLASSES = {
  safe: "border-success/30 bg-success-bg text-success",
  caution: "border-warning/30 bg-warning-bg text-warning",
  at_risk: "border-danger/30 bg-danger-bg text-danger",
} as const;

export default function RiskCheckerPage() {
  const toast = useToast();
  const [stage, setStage] = useState<Stage>("form");
  const [loadingStep, setLoadingStep] = useState(0);
  const [result, setResult] = useState<RiskCheckResult | null>(null);
  const [checkError, setCheckError] = useState<string | null>(null);
  const [confirmedPlan, setConfirmedPlan] = useState<Plan | null>(null);
  const [isConfirming, setIsConfirming] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const schedule = useScheduleInputs("SPayLater");
  const [form, setForm] = useState({
    item_name: "",
    total_price: "",
    num_installments: "6",
    interest_rate: "0",
  });

  // Staged loading messages mirror the real sequential pipeline.
  useEffect(() => {
    if (stage !== "loading") return;
    const timer = setInterval(
      () => setLoadingStep((step) => Math.min(step + 1, LOADING_MESSAGES.length - 1)),
      1600,
    );
    return () => clearInterval(timer);
  }, [stage]);

  const set = (key: string, value: string) => setForm((current) => ({ ...current, [key]: value }));

  const price = Number(form.total_price);
  const count = Number(form.num_installments);
  const interest = Number(form.interest_rate);
  const schedulePreview = previewSchedule(
    price,
    interest || 0,
    count,
    schedule.firstPaymentDate,
    schedule.checkoutCount,
  );

  const handleCheck = async () => {
    const validation: Record<string, string> = {};
    if (!form.item_name.trim()) validation.item_name = "What are you buying?";
    if (!(price > 0)) validation.total_price = "Price must be greater than 0";
    if (!(count >= 1 && count <= MAX_INSTALLMENTS))
      validation.num_installments = `Between 1 and ${MAX_INSTALLMENTS}`;
    if (!(interest >= 0 && interest <= MAX_INTEREST_RATE))
      validation.interest_rate = `Between 0 and ${MAX_INTEREST_RATE}% per month`;
    if (!schedule.purchaseDate) validation.purchase_date = "Required";
    if (!schedule.firstPaymentDate) validation.first_payment_date = "Required";
    setErrors(validation);
    if (Object.keys(validation).length > 0) return;

    setLoadingStep(0);
    setStage("loading");
    setCheckError(null);
    setConfirmedPlan(null);
    try {
      const checkResult = await api.riskCheck({
        item_name: form.item_name.trim(),
        total_price: price,
        provider: schedule.provider,
        num_installments: count,
        purchase_date: schedule.purchaseDate,
        // Only an override is sent; otherwise the backend applies the provider's rule.
        first_payment_date: schedule.firstPaymentOverride || undefined,
        interest_rate: interest,
      });
      setResult(checkResult);
      setStage("result");
    } catch (error) {
      setCheckError(
        error instanceof ApiError
          ? error.message
          : "The risk check failed — make sure the backend is running.",
      );
      setStage("form");
    }
  };

  const handleConfirm = async () => {
    if (!result) return;
    setIsConfirming(true);
    try {
      const plan = await api.riskConfirm(result.check_id);
      setConfirmedPlan(plan);
      toast("success", "Plan saved with its risk score.");
    } catch (error) {
      toast("error", error instanceof ApiError ? error.message : "Couldn't save the plan.");
    } finally {
      setIsConfirming(false);
    }
  };

  const handleDiscard = () => {
    setResult(null);
    setConfirmedPlan(null);
    setStage("form");
  };

  return (
    <div className="flex flex-col gap-4">
      <header>
        <h1 className="text-xl font-semibold text-ink">BNPL Risk Checker</h1>
        <p className="text-[13px] text-ink-secondary">
          Check if a purchase is safe before you commit — forecast first, then score.
        </p>
      </header>

      {stage === "form" && (
        <Card className="max-w-2xl">
          <CardTitle>What are you planning to buy?</CardTitle>
          <CardCaption>The two AI engines evaluate it against your projected balance</CardCaption>
          {checkError && (
            <p role="alert" className="mt-3 rounded-lg border border-danger/30 bg-danger-bg px-3 py-2.5 text-[13px] font-medium text-danger">
              {checkError}
              {checkError.includes("3 months") && (
                <span className="mt-1 block font-normal">
                  Add more history on the <Link className="underline" href="/transactions">Transactions</Link> page first.
                </span>
              )}
            </p>
          )}
          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <TextField
              label="Item name"
              value={form.item_name}
              error={errors.item_name}
              placeholder="e.g. iPhone 16e"
              onChange={(event) => set("item_name", event.target.value)}
            />
            <CurrencyField
              label="Total price"
              value={form.total_price}
              error={errors.total_price}
              placeholder="0.00"
              onChange={(event) => set("total_price", event.target.value)}
            />
            <SelectField
              label="Provider"
              value={schedule.provider}
              onChange={(event) => schedule.setProvider(event.target.value)}
            >
              {BNPL_PROVIDERS.map((provider) => (
                <option key={provider} value={provider}>
                  {provider}
                </option>
              ))}
            </SelectField>
            <TextField
              label="Instalments"
              type="number"
              min="1"
              max={MAX_INSTALLMENTS}
              value={form.num_installments}
              error={errors.num_installments}
              onChange={(event) => set("num_installments", event.target.value)}
            />
            <DateField
              label="Purchase date"
              value={schedule.purchaseDate}
              error={errors.purchase_date}
              onValueChange={schedule.setPurchaseDate}
            />
            <DateField
              label="First payment date (estimate)"
              hint={firstPaymentHint(schedule.provider)}
              value={schedule.firstPaymentDate}
              error={errors.first_payment_date}
              onValueChange={schedule.setFirstPaymentDate}
            />
            <TextField
              label="Fee (% per month)"
              hint="As shown at your provider's checkout, e.g. 1.5. Use 0 for a 0% plan."
              type="number"
              min="0"
              max={MAX_INTEREST_RATE}
              step="0.1"
              value={form.interest_rate}
              error={errors.interest_rate}
              onChange={(event) => set("interest_rate", event.target.value)}
            />
          </div>
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <SchedulePreview schedule={schedulePreview} />
            <Button variant="accent" onClick={handleCheck}>
              Check my risk →
            </Button>
          </div>
        </Card>
      )}

      {stage === "loading" && (
        <Card className="flex max-w-2xl flex-col items-center gap-4 py-14">
          <div className="h-10 w-10 animate-spin rounded-full border-[3px] border-line border-t-accent" />
          <p className="text-sm font-semibold text-ink" aria-live="polite">
            {LOADING_MESSAGES[loadingStep]}
          </p>
          <p className="text-[11px] text-ink-muted">
            ARIMA forecast → instalment overlay → Random Forest risk score → SHAP explanation
          </p>
        </Card>
      )}

      {stage === "result" && result && (
        <div className="flex flex-col gap-4">
          <div className="grid gap-4 md:grid-cols-[300px_1fr]">
            <Card className="flex flex-col items-center justify-center text-center">
              <p className="text-[13px] font-bold text-ink">Purchase health score</p>
              <Gauge score={result.score} size={160} />
              <p className="-mt-1 text-4xl font-bold text-ink">
                {result.score}
                <span className="text-sm font-normal text-ink-secondary">/100</span>
              </p>
              <div className="mt-1.5">
                <Chip tone={labelTone(result.label)}>{LABEL_TEXT[result.label]}</Chip>
              </div>
              <p className="mt-2 text-[11px] text-ink-muted">
                Model confidence: P(risk) = {result.risk_probability.toFixed(2)}
              </p>
            </Card>

            <div className="flex flex-col gap-4">
              <div
                role="status"
                className={`rounded-card border px-4 py-3.5 text-sm font-semibold ${BANNER_CLASSES[result.label]}`}
              >
                💡 {result.recommendation}
              </div>
              <Card>
                <CardTitle>Why this score?</CardTitle>
                <CardCaption>Top factors pushing your risk, from the model</CardCaption>
                <div className="mt-3 flex flex-col gap-2">
                  {result.top_factors.length === 0 && (
                    <p className="text-[13px] text-ink-secondary">
                      Nothing stands out — no single factor is raising your risk noticeably.
                    </p>
                  )}
                  {result.top_factors.map((factor) => (
                    <div
                      key={factor.feature}
                      className="flex items-start gap-2.5 rounded-lg border border-line bg-surface-2 px-3 py-2.5 text-[13px] text-ink"
                    >
                      <span
                        aria-hidden
                        className={
                          factor.shap_value > 0.05 ? "text-danger" : "text-warning"
                        }
                      >
                        ●
                      </span>
                      {factor.message}
                    </div>
                  ))}
                </div>
                <p className="mt-2.5 text-[10px] text-ink-muted">
                  Explained by SHAP (explainable AI) on the Random Forest classifier
                </p>
              </Card>
            </div>
          </div>

          <Card>
            <CardTitle>Balance impact — next 3 months</CardTitle>
            <CardCaption>
              Weekly projected balance from the ARIMA forecast, with your proposed instalments applied
            </CardCaption>
            <div className="mt-3">
              <OverlayChart
                withoutPurchase={result.curves.without_purchase}
                withPurchase={result.curves.with_purchase}
              />
            </div>
          </Card>

          <div className="grid gap-4 md:grid-cols-[1fr_300px]">
            <Card>
              <CardTitle>Proposed instalment schedule</CardTitle>
              <CardCaption>
                {form.item_name} · {schedule.provider}
              </CardCaption>
              <div className="mt-3 overflow-x-auto">
                <table className="w-full text-left text-[13px]">
                  <thead>
                    <tr className="border-b border-line text-[11px] text-ink-secondary">
                      <th className="py-1.5 pr-3 font-semibold">#</th>
                      <th className="py-1.5 pr-3 font-semibold">Due date</th>
                      <th className="py-1.5 text-right font-semibold">Amount</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {result.proposed_schedule.map((item) => (
                      <tr key={item.seq}>
                        <td className="py-2 pr-3 text-ink-muted">{item.seq}</td>
                        <td className="py-2 pr-3">
                          {formatDate(item.due_date)}
                          {item.paid_at_checkout && (
                            <span className="ml-2 text-[11px] font-medium text-success">
                              Paid at checkout
                            </span>
                          )}
                        </td>
                        <td className="py-2 text-right font-semibold">{formatRM(item.amount)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>

            <Card className="flex h-fit flex-col gap-3">
              {confirmedPlan ? (
                <>
                  <p className="text-[13px] font-semibold text-success">✓ Saved to your plans</p>
                  <Link href={`/plans/${confirmedPlan.id}`}>
                    <Button variant="accent" className="w-full">
                      View plan →
                    </Button>
                  </Link>
                  <Button variant="secondary" className="w-full" onClick={handleDiscard}>
                    Check another purchase
                  </Button>
                </>
              ) : (
                <>
                  <p className="text-[13px] text-ink-secondary">
                    Happy with the risk? Save it as a tracked plan with this score attached.
                  </p>
                  <Button
                    variant="accent"
                    className="w-full"
                    onClick={handleConfirm}
                    disabled={isConfirming}
                  >
                    {isConfirming ? "Saving…" : "Confirm & save to plans"}
                  </Button>
                  <Button variant="secondary" className="w-full" onClick={handleDiscard}>
                    Discard
                  </Button>
                </>
              )}
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
