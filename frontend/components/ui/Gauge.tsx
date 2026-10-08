// Semicircular health gauge 0–100 — custom SVG arc matching the mockup.
import { HEALTH_CAUTION_MIN, HEALTH_SAFE_MIN } from "@/lib/constants";

const ARC_COLORS = { danger: "#E24B4A", warning: "#EF9F27", success: "#639922" };

function polar(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = ((angleDeg - 180) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function arcPath(cx: number, cy: number, r: number, startPct: number, endPct: number) {
  const start = polar(cx, cy, r, startPct * 1.8);
  const end = polar(cx, cy, r, endPct * 1.8);
  return `M ${start.x.toFixed(1)} ${start.y.toFixed(1)} A ${r} ${r} 0 0 1 ${end.x.toFixed(1)} ${end.y.toFixed(1)}`;
}

export function Gauge({ score, size = 180 }: { score: number; size?: number }) {
  const clamped = Math.max(0, Math.min(100, score));
  const needleAngle = clamped * 1.8 - 90;
  const gap = 1.5;

  return (
    <svg
      width={size}
      height={size * 0.6}
      viewBox="0 0 200 120"
      role="img"
      aria-label={`Financial health score ${clamped} out of 100`}
    >
      <path d={arcPath(100, 100, 80, 0, HEALTH_CAUTION_MIN - gap)} stroke={ARC_COLORS.danger} strokeWidth="16" fill="none" strokeLinecap="round" />
      <path d={arcPath(100, 100, 80, HEALTH_CAUTION_MIN + gap, HEALTH_SAFE_MIN - gap)} stroke={ARC_COLORS.warning} strokeWidth="16" fill="none" strokeLinecap="round" />
      <path d={arcPath(100, 100, 80, HEALTH_SAFE_MIN + gap, 100)} stroke={ARC_COLORS.success} strokeWidth="16" fill="none" strokeLinecap="round" />
      <text x="14" y="118" className="fill-ink-muted" style={{ fontSize: 9 }}>0</text>
      <text x="95" y="12" className="fill-ink-muted" style={{ fontSize: 9 }}>50</text>
      <text x="176" y="118" className="fill-ink-muted" style={{ fontSize: 9 }}>100</text>
      <g transform={`rotate(${needleAngle} 100 100)`}>
        <line x1="100" y1="100" x2="100" y2="34" stroke="#1C1C1A" strokeWidth="3" strokeLinecap="round" />
      </g>
      <circle cx="100" cy="100" r="7" fill="#1C1C1A" />
    </svg>
  );
}
