"use client";
// Delete-plan confirmation for a plan that has paid instalments. Shows the transactions those
// payments logged and asks whether to delete them too. The safe choice — keep them — is the
// default and what Cancel / closing the dialog amounts to: real financial records are never
// deleted unless the user explicitly picks that option.
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { api } from "@/lib/api";
import { formatDate, formatRM } from "@/lib/format";
import type { Plan } from "@/lib/types";
import { useApi } from "@/lib/useApi";

type Props = {
  plan: Plan;
  isDeleting: boolean;
  onCancel: () => void;
  onConfirm: (deleteTransactions: boolean) => void;
};

type Choice = "keep" | "delete";

const PREVIEW_ROWS = 6;

/** Mounted only while open, so each opening re-checks the plan's transactions and resets to "keep". */
export function DeletePlanDialog({ plan, isDeleting, onCancel, onConfirm }: Props) {
  const { data, isLoading, error } = useApi(() => api.planTransactions(plan.id), [plan.id]);
  const [choice, setChoice] = useState<Choice>("keep");

  const count = data?.count ?? 0;
  const hasTransactions = count > 0;

  return (
    <Modal isOpen title={`Delete "${plan.item_name}"?`} onClose={onCancel} maxWidth="max-w-xl">
      {isLoading && (
        <p className="text-[13px] text-ink-secondary">Checking which transactions this plan logged…</p>
      )}

      {error && (
        <p role="alert" className="rounded-lg border border-danger/30 bg-danger-bg px-3 py-2.5 text-[13px] text-danger">
          Couldn&apos;t check this plan&apos;s transactions ({error}). You can still delete the plan; its
          transactions will be kept.
        </p>
      )}

      {data && !hasTransactions && (
        <p className="text-[13px] text-ink-secondary">
          This plan has {plan.paid_count} paid {plan.paid_count === 1 ? "instalment" : "instalments"}, but no
          matching logged transactions were found, so there is nothing to keep or delete in Transactions.
        </p>
      )}

      {data && hasTransactions && (
        <div className="flex flex-col gap-3">
          <p className="text-[13px] text-ink">
            Paying this plan&apos;s instalments logged <strong>{count}</strong>{" "}
            {count === 1 ? "transaction" : "transactions"} totalling <strong>{formatRM(data.total)}</strong>:
          </p>
          <ul className="max-h-40 divide-y divide-line overflow-y-auto rounded-lg border border-line bg-surface-2 text-[12px]">
            {data.items.slice(0, PREVIEW_ROWS).map((item) => (
              <li key={item.id} className="flex items-center justify-between gap-3 px-3 py-1.5">
                <span className="truncate text-ink-secondary">
                  {formatDate(item.date)} · {item.description}
                </span>
                <span className="font-medium text-ink">{formatRM(item.amount)}</span>
              </li>
            ))}
            {data.items.length > PREVIEW_ROWS && (
              <li className="px-3 py-1.5 text-ink-muted">…and {data.items.length - PREVIEW_ROWS} more</li>
            )}
          </ul>

          <fieldset className="flex flex-col gap-2">
            <legend className="mb-1 text-xs font-semibold text-ink">What should happen to them?</legend>
            <label className="flex cursor-pointer items-start gap-2 rounded-lg border border-line p-2.5 text-[13px] has-[:checked]:border-accent has-[:checked]:bg-accent-bg">
              <input
                type="radio"
                name="delete-plan-transactions"
                className="mt-0.5"
                checked={choice === "keep"}
                onChange={() => setChoice("keep")}
              />
              <span>
                <strong>Keep these transactions</strong>
                <span className="block text-[12px] text-ink-secondary">
                  For instalments you really paid — you just want to stop tracking the plan.
                </span>
              </span>
            </label>
            <label className="flex cursor-pointer items-start gap-2 rounded-lg border border-line p-2.5 text-[13px] has-[:checked]:border-danger has-[:checked]:bg-danger-bg">
              <input
                type="radio"
                name="delete-plan-transactions"
                className="mt-0.5"
                checked={choice === "delete"}
                onChange={() => setChoice("delete")}
              />
              <span>
                <strong>
                  Also delete these {count} {count === 1 ? "transaction" : "transactions"} ({formatRM(data.total)})
                </strong>
                <span className="block text-[12px] text-ink-secondary">
                  For a mistake or a test plan. They stop counting toward your spending and forecast, and the
                  money goes back to your balance. This can&apos;t be undone.
                </span>
              </span>
            </label>
          </fieldset>
          <p className="text-[11px] text-ink-muted">
            Only transactions logged by marking this plan&apos;s instalments paid are listed. Ones you added by
            hand are never deleted.
          </p>
        </div>
      )}

      <div className="mt-5 flex justify-end gap-2">
        <Button variant="secondary" onClick={onCancel} disabled={isDeleting}>
          Cancel
        </Button>
        <Button
          variant="danger"
          disabled={isDeleting || isLoading}
          onClick={() => onConfirm(hasTransactions && choice === "delete")}
        >
          {isDeleting ? "Deleting…" : "Delete plan"}
        </Button>
      </div>
    </Modal>
  );
}
