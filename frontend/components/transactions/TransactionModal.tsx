"use client";
// Add/edit transaction form with inline validation mirroring backend rules.
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";
import { CurrencyField, DateField, SelectField, TextField } from "@/components/ui/fields";
import { api, ApiError } from "@/lib/api";
import { TRANSACTION_CATEGORIES } from "@/lib/constants";
import { todayISO } from "@/lib/format";
import type { Transaction, TransactionInput, TransactionType } from "@/lib/types";

type Props = {
  isOpen: boolean;
  editing: Transaction | null;
  onClose: () => void;
  onSaved: () => void;
};

export function TransactionModal({ isOpen, editing, onClose, onSaved }: Props) {
  const toast = useToast();
  const [isSaving, setIsSaving] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const [form, setForm] = useState(() => defaultForm(editing));
  const [lastEditingId, setLastEditingId] = useState(editing?.id ?? null);
  if ((editing?.id ?? null) !== lastEditingId) {
    setLastEditingId(editing?.id ?? null);
    setForm(defaultForm(editing));
    setErrors({});
  }

  const set = (key: string, value: string | boolean) =>
    setForm((current) => ({ ...current, [key]: value }));

  const handleSubmit = async () => {
    const validation: Record<string, string> = {};
    const amount = Number(form.amount);
    if (!form.amount || !Number.isFinite(amount) || amount <= 0) {
      validation.amount = "Amount must be greater than 0";
    }
    if (!form.date) validation.date = "Date is required";
    setErrors(validation);
    if (Object.keys(validation).length > 0) return;

    const payload: TransactionInput = {
      date: form.date,
      amount,
      type: form.type as TransactionType,
      category: form.category,
      description: form.description || null,
      account_name: form.account_name || null,
      is_bnpl: form.is_bnpl,
    };

    setIsSaving(true);
    try {
      if (editing) {
        await api.updateTransaction(editing.id, payload);
        toast("success", "Transaction updated.");
      } else {
        await api.createTransaction(payload);
        toast("success", "Transaction added.");
      }
      onSaved();
      onClose();
    } catch (error) {
      toast("error", error instanceof ApiError ? error.message : "Couldn't save the transaction.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Modal isOpen={isOpen} title={editing ? "Edit transaction" : "Add transaction"} onClose={onClose}>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <DateField
          label="Date"
          value={form.date}
          error={errors.date}
          onValueChange={(value) => set("date", value)}
        />
        <CurrencyField
          label="Amount"
          value={form.amount}
          error={errors.amount}
          placeholder="0.00"
          onChange={(event) => set("amount", event.target.value)}
        />
        <SelectField label="Type" value={form.type} onChange={(event) => set("type", event.target.value)}>
          <option value="expense">Expense</option>
          <option value="income">Income</option>
          <option value="savings">Savings</option>
        </SelectField>
        <SelectField
          label="Category"
          value={form.category}
          onChange={(event) => set("category", event.target.value)}
        >
          {TRANSACTION_CATEGORIES.map((category) => (
            <option key={category} value={category}>
              {category}
            </option>
          ))}
        </SelectField>
        <TextField
          label="Description (optional)"
          value={form.description}
          placeholder="e.g. Mamak with friends"
          onChange={(event) => set("description", event.target.value)}
        />
        <TextField
          label="Account (optional)"
          value={form.account_name}
          placeholder="e.g. Maybank, TnG eWallet"
          onChange={(event) => set("account_name", event.target.value)}
        />
      </div>
      <label className="mt-3 flex items-center gap-2 text-[13px] text-ink-secondary">
        <input
          type="checkbox"
          checked={form.is_bnpl}
          onChange={(event) => set("is_bnpl", event.target.checked)}
          className="h-4 w-4 accent-[#185FA5]"
        />
        This is a BNPL instalment payment
      </label>
      <div className="mt-5 flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button onClick={handleSubmit} disabled={isSaving}>
          {isSaving ? "Saving…" : editing ? "Save changes" : "Add transaction"}
        </Button>
      </div>
    </Modal>
  );
}

function defaultForm(editing: Transaction | null) {
  return {
    date: editing?.date ?? todayISO(),
    amount: editing ? String(editing.amount) : "",
    type: (editing?.type ?? "expense") as string,
    category: editing?.category ?? "Food",
    description: editing?.description ?? "",
    account_name: editing?.account_name ?? "",
    is_bnpl: editing?.is_bnpl ?? false,
  };
}
