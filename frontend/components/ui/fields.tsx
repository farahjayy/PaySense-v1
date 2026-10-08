"use client";
// Form field primitives with consistent labels + validation messages.
import { useRef, useState } from "react";
import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";

import { displayToIso, isoToDisplay } from "@/lib/format";

function FieldShell({
  label,
  error,
  hint,
  children,
}: {
  label: string;
  error?: string | null;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1 text-xs font-medium text-ink-secondary">
      {label}
      {children}
      {hint && <span className="text-[11px] font-normal text-ink-muted">{hint}</span>}
      {error && <span className="text-[11px] font-medium text-danger">{error}</span>}
    </label>
  );
}

const INPUT_CLASSES =
  "h-9 rounded-lg border border-line bg-surface px-3 text-[13px] font-normal text-ink placeholder:text-ink-muted hover:border-ink-muted";

export function TextField({
  label,
  error,
  hint,
  ...rest
}: InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string | null; hint?: string }) {
  return (
    <FieldShell label={label} error={error} hint={hint}>
      <input className={INPUT_CLASSES} {...rest} />
    </FieldShell>
  );
}

export function CurrencyField({
  label,
  error,
  ...rest
}: InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string | null }) {
  return (
    <FieldShell label={label} error={error}>
      <div className="relative">
        <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[13px] text-ink-muted">
          RM
        </span>
        <input
          type="number"
          inputMode="decimal"
          step="0.01"
          min="0"
          className={`${INPUT_CLASSES} w-full pl-10`}
          {...rest}
        />
      </div>
    </FieldShell>
  );
}

const DATE_DIGITS = 8;

/** Digits only, masked as dd/mm/yyyy while typing. */
function maskDate(raw: string): string {
  const digits = raw.replace(/\D/g, "").slice(0, DATE_DIGITS);
  return [digits.slice(0, 2), digits.slice(2, 4), digits.slice(4)].filter(Boolean).join("/");
}

/**
 * Date input that always reads dd/mm/yyyy. A native <input type="date"> shows the browser's
 * own locale format (and cannot be changed from the page), so this is a masked text field
 * with a calendar button that opens the native picker. `value` and `onValueChange` use ISO
 * yyyy-mm-dd; half-typed or impossible dates are never passed on and snap back on blur.
 */
export function DateField({
  label,
  error,
  hint,
  value,
  onValueChange,
}: {
  label: string;
  value: string;
  onValueChange: (iso: string) => void;
  error?: string | null;
  hint?: string;
}) {
  const [text, setText] = useState(isoToDisplay(value));
  const [syncedValue, setSyncedValue] = useState(value);
  const pickerRef = useRef<HTMLInputElement>(null);

  // The parent changed the date (e.g. a new provider re-derives it): show it.
  if (value !== syncedValue) {
    setSyncedValue(value);
    setText(isoToDisplay(value));
  }

  const handleType = (raw: string) => {
    const masked = maskDate(raw);
    setText(masked);
    const iso = displayToIso(masked);
    if (iso) {
      setSyncedValue(iso);
      onValueChange(iso);
    }
  };

  return (
    <FieldShell label={label} error={error} hint={hint}>
      <div className="relative">
        <input
          type="text"
          inputMode="numeric"
          placeholder="dd/mm/yyyy"
          maxLength={10}
          className={`${INPUT_CLASSES} w-full pr-9`}
          value={text}
          onChange={(event) => handleType(event.target.value)}
          onBlur={() => {
            if (!displayToIso(text)) setText(isoToDisplay(value));
          }}
        />
        <button
          type="button"
          aria-label={`Pick ${label} from a calendar`}
          className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-ink-muted hover:text-ink"
          onClick={() => pickerRef.current?.showPicker?.()}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
            <rect x="2" y="3" width="12" height="11" rx="1.5" stroke="currentColor" strokeWidth="1.3" />
            <path d="M2 6.5h12M5.5 1.5v3M10.5 1.5v3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
          </svg>
        </button>
        <input
          ref={pickerRef}
          type="date"
          tabIndex={-1}
          aria-hidden
          value={value}
          onChange={(event) => event.target.value && onValueChange(event.target.value)}
          className="pointer-events-none absolute bottom-0 right-2 h-px w-px opacity-0"
        />
      </div>
    </FieldShell>
  );
}

export function SelectField({
  label,
  error,
  hint,
  children,
  ...rest
}: SelectHTMLAttributes<HTMLSelectElement> & {
  label: string;
  error?: string | null;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <FieldShell label={label} error={error} hint={hint}>
      <select className={`${INPUT_CLASSES} appearance-auto`} {...rest}>
        {children}
      </select>
    </FieldShell>
  );
}
