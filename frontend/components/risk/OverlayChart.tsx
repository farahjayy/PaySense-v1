"use client";
// Balance impact chart: without-this-X vs with-this-X weekly curves, annotated so the shape
// reads at a glance without any interaction — a start label, a full label on the first
// FUTURE payment step, short amount labels on later steps. A checkout-paid instalment (e.g.
// Atome's first) is money that already left the account at the purchase moment, not a future
// payment date, so it is called out in the start label instead of as a step. Full detail
// (exact date, exact balance, "instalment X of Y") is tap-to-reveal via a click handler on
// every point, which works identically for mouse click and touch tap — no hover-only Recharts
// Tooltip is used, since hover does not exist on phones.
import { useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts";

import { LOW_BALANCE_THRESHOLD_RM } from "@/lib/constants";
import { formatDate, formatRM } from "@/lib/format";
import type { ChartScheduleItem, CurvePoint } from "@/lib/types";

interface Group {
  index: number;
  amount: number;
  items: ChartScheduleItem[];
  isCheckout: boolean;
}

/** Groups schedule items into the curve week each lands in — mirrors the backend's own
 * (week_start, week_end] bucketing (weekly_balance_curve). Index 0 is always just the
 * starting snapshot: the backend's own due-today handling still lands the MECHANICAL
 * subtraction in week 1 / index 1, one week later than the charge really happened. A
 * checkout-paid instalment (e.g. Atome's first) is money that left the account at the
 * purchase moment — that is a fact, not a curve artifact — so it is always anchored to
 * index 0, overriding wherever the curve numerically reflects it. Every other (future)
 * instalment searches from index 1, matching the curve exactly. */
function computeGroups(points: CurvePoint[], schedule: ChartScheduleItem[]): Group[] {
  const byIndex = new Map<number, ChartScheduleItem[]>();
  for (const item of schedule) {
    const index = item.paid_at_checkout
      ? 0
      : points.findIndex((point, i) => i > 0 && item.due_date <= point.date);
    if (index < 0) continue; // beyond the visible window: nothing to annotate
    byIndex.set(index, [...(byIndex.get(index) ?? []), item]);
  }
  return [...byIndex.entries()]
    .sort(([a], [b]) => a - b)
    .map(([index, items]) => ({
      index,
      items,
      amount: items.reduce((sum, i) => sum + i.amount, 0),
      isCheckout: items.some((i) => i.paid_at_checkout),
    }));
}

function textAnchorFor(index: number, lastIndex: number): "start" | "middle" | "end" {
  if (index <= 0) return "start";
  if (index >= lastIndex - 1) return "end";
  return "middle";
}

type Coordinate = number | string | undefined;

function toNumber(value: Coordinate): number | null {
  if (value === undefined) return null;
  const num = typeof value === "number" ? value : Number(value);
  return Number.isNaN(num) ? null : num;
}

function StartEndLabel({ x, y, text }: { x?: Coordinate; y?: Coordinate; text: string }) {
  const numX = toNumber(x);
  const numY = toNumber(y);
  if (numX === null || numY === null) return null;
  return (
    <text x={numX} y={numY - 10} textAnchor="start" fontSize={9} fill="#6B6A63">
      {text}
    </text>
  );
}

function StepLabel({
  x,
  y,
  text,
  index,
  lastIndex,
  emphasise,
}: {
  x?: Coordinate;
  y?: Coordinate;
  text: string;
  index: number;
  lastIndex: number;
  emphasise: boolean;
}) {
  const numX = toNumber(x);
  const numY = toNumber(y);
  if (numX === null || numY === null) return null;
  return (
    <text
      x={numX}
      y={numY - 10}
      textAnchor={textAnchorFor(index, lastIndex)}
      fontSize={emphasise ? 10 : 9}
      fontWeight={emphasise ? 600 : 400}
      fill={emphasise ? "#A32D2D" : "#854F0B"}
    >
      {text}
    </text>
  );
}

export function OverlayChart({
  withoutPurchase,
  withPurchase,
  schedule = [],
  subject = "purchase",
}: {
  withoutPurchase: CurvePoint[];
  withPurchase: CurvePoint[];
  /** Instalments as they stood when this check ran — drives the payment-step labels. */
  schedule?: ChartScheduleItem[];
  /** What the overlay compares: "purchase" (pre-decision, default) or "plan" (an existing plan's own impact, shown after the fact). */
  subject?: "purchase" | "plan";
}) {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);

  const withMap = new Map(withPurchase.map((point) => [point.date, point.balance]));
  const data = withoutPurchase.map((point) => ({
    date: point.date,
    without: point.balance,
    with: withMap.get(point.date) ?? null,
  }));
  const lastIndex = data.length - 1;

  const groups = computeGroups(withoutPurchase, schedule);
  const groupByIndex = new Map(groups.map((group) => [group.index, group]));
  // Only future payments get an arrow-label on the line; a checkout charge is announced
  // once, in the start label, instead of at whatever week the chart happens to show its
  // effect (misleading, since it did not actually happen "on" that date).
  const futureSteps = groups.filter((group) => !group.isCheckout);
  const checkoutTotal = schedule
    .filter((item) => item.paid_at_checkout)
    .reduce((sum, item) => sum + item.amount, 0);

  const minBalance = Math.min(0, ...withPurchase.map((p) => p.balance), ...withoutPurchase.map((p) => p.balance));

  const selected = selectedIndex === null ? null : { point: withoutPurchase[selectedIndex], group: groupByIndex.get(selectedIndex) };

  const startLabelText =
    checkoutTotal > 0
      ? `Purchase — ${formatRM(checkoutTotal)} charged at checkout`
      : subject === "plan"
        ? "Today — nothing charged yet"
        : "Purchase — nothing charged yet";

  return (
    <div className="w-full">
      <div className="h-72 w-full">
        <ResponsiveContainer>
          <LineChart data={data} margin={{ top: 20, right: 16, left: 8, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke="#EDEBE3" />
            <XAxis
              dataKey="date"
              tickFormatter={formatDate}
              tick={{ fontSize: 10, fill: "#9A988F" }}
              axisLine={{ stroke: "#E3E1D9" }}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fontSize: 10, fill: "#9A988F" }}
              axisLine={false}
              tickLine={false}
              width={52}
              tickFormatter={(value: number) => `RM${Math.round(value)}`}
            />
            {minBalance < 0 && (
              <ReferenceArea y1={minBalance * 1.1} y2={0} fill="#FCEBEB" fillOpacity={0.6} />
            )}
            <ReferenceLine y={0} stroke="#A32D2D" strokeWidth={1} strokeDasharray="4 3" />
            <ReferenceLine
              y={LOW_BALANCE_THRESHOLD_RM}
              stroke="#854F0B"
              strokeWidth={1}
              strokeDasharray="2 4"
              label={{
                value: `RM${LOW_BALANCE_THRESHOLD_RM} buffer`,
                position: "insideTopRight",
                fontSize: 9,
                fill: "#854F0B",
              }}
            />
            <Line
              type="monotone"
              dataKey="without"
              name={`Without this ${subject}`}
              stroke="#185FA5"
              strokeWidth={2.5}
              dot={false}
              activeDot={false}
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="with"
              name={`With this ${subject}`}
              stroke="#E24B4A"
              strokeWidth={2.5}
              strokeDasharray="6 4"
              isAnimationActive={false}
              label={(props: { x?: Coordinate; y?: Coordinate; index?: number }) => {
                const index = props.index ?? -1;
                if (index === 0) {
                  return <StartEndLabel key="start" x={props.x} y={props.y} text={startLabelText} />;
                }
                const stepIndex = futureSteps.findIndex((step) => step.index === index);
                if (stepIndex === -1) return null;
                const step = futureSteps[stepIndex];
                const isFirstStep = stepIndex === 0;
                return (
                  <StepLabel
                    key={`step-${index}`}
                    x={props.x}
                    y={props.y}
                    index={index}
                    lastIndex={lastIndex}
                    emphasise={isFirstStep}
                    text={isFirstStep ? `Next payment: -${formatRM(step.amount)}` : `-${formatRM(step.amount)}`}
                  />
                );
              }}
              dot={(props: { cx?: number; cy?: number; value?: number; index?: number }) => {
                const index = props.index ?? -1;
                const isDip = (props.value ?? Infinity) < LOW_BALANCE_THRESHOLD_RM;
                const isStep = groupByIndex.has(index);
                const isSelected = index === selectedIndex;
                const radius = isSelected ? 6 : isDip || isStep ? 4 : 3;
                return (
                  <g
                    key={index}
                    onClick={() => setSelectedIndex((current) => (current === index ? null : index))}
                    style={{ cursor: "pointer" }}
                  >
                    {/* Invisible larger hit-area so a finger tap doesn't need to land exactly on the small dot. */}
                    <circle cx={props.cx} cy={props.cy} r={12} fill="transparent" />
                    <circle
                      cx={props.cx}
                      cy={props.cy}
                      r={radius}
                      fill={isDip ? "#A32D2D" : isSelected ? "#E24B4A" : "#fff"}
                      stroke="#E24B4A"
                      strokeWidth={2}
                    />
                  </g>
                );
              }}
              activeDot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-1 flex justify-center gap-4 text-[11px] text-ink-secondary">
        <span className="flex items-center gap-1.5">
          <i className="inline-block h-2 w-4 rounded-sm bg-accent" /> without this {subject}
        </span>
        <span className="flex items-center gap-1.5">
          <i className="inline-block h-2 w-4 rounded-sm bg-chart-red" /> with this {subject}
        </span>
      </div>

      <div className="mt-2 min-h-[52px] rounded-lg border border-line bg-surface-2 px-3 py-2 text-[12px]">
        {selected ? (
          <>
            <p className="font-semibold text-ink">{formatDate(selected.point.date)}</p>
            <p className="text-ink-secondary">
              Without: {formatRM(selected.point.balance)} · With:{" "}
              {formatRM(
                // Index 0's raw curve value is always the unchanged starting balance (the
                // backend curve only starts reflecting subtractions from index 1 on) — for a
                // checkout charge, which truthfully happened right at this point, show the
                // balance net of it instead of repeating the unchanged number next to
                // "charged at checkout" below.
                selectedIndex === 0 && selected.group?.isCheckout
                  ? selected.point.balance - selected.group.amount
                  : (withMap.get(selected.point.date) ?? selected.point.balance),
              )}
            </p>
            {selected.group ? (
              <p className="mt-0.5 font-medium text-danger">
                {selected.group.items
                  .map((item) =>
                    item.paid_at_checkout
                      ? `Instalment ${item.seq} of ${item.num_installments} — charged at checkout, -${formatRM(item.amount)}`
                      : `Instalment ${item.seq} of ${item.num_installments} — -${formatRM(item.amount)}`,
                  )
                  .join(", ")}
              </p>
            ) : (
              <p className="mt-0.5 text-ink-muted">No payment lands this week.</p>
            )}
          </>
        ) : (
          <p className="text-ink-muted">Tap a point on the chart for its exact date and balance.</p>
        )}
      </div>
    </div>
  );
}
