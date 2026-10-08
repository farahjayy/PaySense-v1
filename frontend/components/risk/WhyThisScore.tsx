// SHAP "why this score" factor list — shared by the live Risk Checker result and the frozen
// risk report on a plan, so the two never drift into different markup for the same data shape.
import { Card, CardCaption, CardTitle } from "@/components/ui/Card";
import type { RiskFactor } from "@/lib/types";

type Props = {
  factors: RiskFactor[];
};

export function WhyThisScore({ factors }: Props) {
  return (
    <Card>
      <CardTitle>Why this score?</CardTitle>
      <CardCaption>Top factors pushing your risk, from the model</CardCaption>
      <div className="mt-3 flex flex-col gap-2">
        {factors.length === 0 && (
          <p className="text-[13px] text-ink-secondary">
            Nothing stands out — no single factor is raising your risk noticeably.
          </p>
        )}
        {factors.map((factor) => (
          <div
            key={factor.feature}
            className="flex items-start gap-2.5 rounded-lg border border-line bg-surface-2 px-3 py-2.5 text-[13px] text-ink"
          >
            <span aria-hidden className={factor.shap_value > 0.05 ? "text-danger" : "text-warning"}>
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
  );
}
