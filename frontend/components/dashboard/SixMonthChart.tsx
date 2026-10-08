"use client";
// Grouped income/expense bars: 3 historical solid + 3 forecast (translucent).
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { formatMonth, formatRM } from "@/lib/format";
import type { ChartMonth } from "@/lib/types";

const COLORS = {
  income: "#185FA5",
  incomeForecast: "#85B7EB",
  expense: "#E24B4A",
  expenseForecast: "#F0A9A8",
};

interface TooltipPayloadEntry {
  name?: string;
  value?: number | string;
  color?: string;
}

function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: TooltipPayloadEntry[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  const entry = payload[0] as TooltipPayloadEntry & { payload?: ChartMonth };
  const isForecast = entry?.payload?.is_forecast;
  return (
    <div className="rounded-lg border border-line bg-surface px-3 py-2 text-xs shadow-md">
      <p className="mb-1 font-semibold text-ink">
        {formatMonth(String(label))}
        {isForecast && <span className="ml-1.5 font-medium text-accent">AI forecast</span>}
      </p>
      {payload.map((item) => (
        <p key={item.name} style={{ color: item.color }}>
          {item.name}: {formatRM(Number(item.value))}
        </p>
      ))}
    </div>
  );
}

export function SixMonthChart({ data }: { data: ChartMonth[] }) {
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
          <CartesianGrid vertical={false} stroke="#EDEBE3" />
          <XAxis
            dataKey="month"
            tickFormatter={formatMonth}
            tick={{ fontSize: 11, fill: "#9A988F" }}
            axisLine={{ stroke: "#E3E1D9" }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "#9A988F" }}
            axisLine={false}
            tickLine={false}
            width={44}
            tickFormatter={(v: number) => `${Math.round(v / 100) / 10}k`}
          />
          <Tooltip content={<ChartTooltip />} cursor={{ fill: "#F4F3EF" }} />
          <Legend
            wrapperStyle={{ fontSize: 11 }}
            formatter={(value: string) => <span className="text-ink-secondary">{value}</span>}
          />
          <Bar dataKey="income" name="Income" radius={[3, 3, 0, 0]}>
            {data.map((entry) => (
              <Cell
                key={entry.month}
                fill={entry.is_forecast ? COLORS.incomeForecast : COLORS.income}
                stroke={entry.is_forecast ? COLORS.income : undefined}
                strokeDasharray={entry.is_forecast ? "4 3" : undefined}
              />
            ))}
          </Bar>
          <Bar dataKey="expenses" name="Expenses" radius={[3, 3, 0, 0]}>
            {data.map((entry) => (
              <Cell
                key={entry.month}
                fill={entry.is_forecast ? COLORS.expenseForecast : COLORS.expense}
                stroke={entry.is_forecast ? COLORS.expense : undefined}
                strokeDasharray={entry.is_forecast ? "4 3" : undefined}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
