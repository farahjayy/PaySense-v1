"use client";
// Balance impact chart: without-purchase vs with-purchase weekly curves.
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { LOW_BALANCE_THRESHOLD_RM } from "@/lib/constants";
import { formatRM, formatShortDate } from "@/lib/format";
import type { CurvePoint } from "@/lib/types";

interface TooltipEntry {
  name?: string;
  value?: number | string;
  color?: string;
}

function CurveTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: TooltipEntry[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-line bg-surface px-3 py-2 text-xs shadow-md">
      <p className="mb-1 font-semibold text-ink">{formatShortDate(String(label))}</p>
      {payload.map((entry) => (
        <p key={entry.name} style={{ color: entry.color }}>
          {entry.name}: {formatRM(Number(entry.value))}
        </p>
      ))}
    </div>
  );
}

export function OverlayChart({
  withoutPurchase,
  withPurchase,
}: {
  withoutPurchase: CurvePoint[];
  withPurchase: CurvePoint[];
}) {
  const withMap = new Map(withPurchase.map((point) => [point.date, point.balance]));
  const data = withoutPurchase.map((point) => ({
    date: point.date,
    without: point.balance,
    with: withMap.get(point.date) ?? null,
  }));

  const minBalance = Math.min(0, ...withPurchase.map((p) => p.balance), ...withoutPurchase.map((p) => p.balance));

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 8, right: 12, left: 8, bottom: 0 }}>
          <CartesianGrid vertical={false} stroke="#EDEBE3" />
          <XAxis
            dataKey="date"
            tickFormatter={formatShortDate}
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
          <Tooltip content={<CurveTooltip />} />
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
            name="Without this purchase"
            stroke="#185FA5"
            strokeWidth={2.5}
            dot={false}
            activeDot={{ r: 4 }}
          />
          <Line
            type="monotone"
            dataKey="with"
            name="With this purchase"
            stroke="#E24B4A"
            strokeWidth={2.5}
            strokeDasharray="6 4"
            dot={(props: { cx?: number; cy?: number; value?: number; index?: number }) => {
              const isDip = (props.value ?? Infinity) < LOW_BALANCE_THRESHOLD_RM;
              return (
                <circle
                  key={props.index}
                  cx={props.cx}
                  cy={props.cy}
                  r={isDip ? 4 : 0}
                  fill="#A32D2D"
                  stroke="#FCEBEB"
                  strokeWidth={2}
                />
              );
            }}
            activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
      <div className="mt-1 flex justify-center gap-4 text-[11px] text-ink-secondary">
        <span className="flex items-center gap-1.5">
          <i className="inline-block h-2 w-4 rounded-sm bg-accent" /> without this purchase
        </span>
        <span className="flex items-center gap-1.5">
          <i className="inline-block h-2 w-4 rounded-sm bg-chart-red" /> with this purchase
        </span>
      </div>
    </div>
  );
}
