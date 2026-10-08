"use client";
// Create-plan form with live instalment schedule preview as the user types.
import { useState } from "react";

import { SchedulePreview } from "@/components/plans/SchedulePreview";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";
import { CurrencyField, DateField, SelectField, TextField } from "@/components/ui/fields";
import { api, ApiError } from "@/lib/api";
import { BNPL_PROVIDERS, MAX_INSTALLMENTS, MAX_INTEREST_RATE } from "@/lib/constants";
import { formatDate, formatRM } from "@/lib/format";
import { firstPaymentHint, previewSchedule } from "@/lib/schedule";
import { useScheduleInputs } from "@/lib/useScheduleInputs";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  onCreated: () => void;
};

/** The form is mounted only while open, so every opening starts blank (no leftovers from the last plan). */
export function CreatePlanModal(props: Props) {
  return props.isOpen ? <CreatePlanForm {...props} /> : null;
}

function CreatePlanForm({ isOpen, onClose, onCreated }: Props) {
  const toast = useToast();
  const [isSaving, setIsSaving] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const inputs = useScheduleInputs("SPayLater");
  const [form, setForm] = useState({
    item_name: "",
    total_price: "",
    interest_rate: "0",
    num_installments: "3",
  });

  const set = (key: string, value: string) => setForm((current) => ({ ...current, [key]: value }));

  const price = Number(form.total_price);
  const interest = Number(form.interest_rate);
  const count = Number(form.num_installments);
  const schedule = previewSchedule(
    price,
    interest || 0,
    count,
    inputs.firstPaymentDate,
    inputs.checkoutCount,
  );

  const handleSubmit = async () => {
    const validation: Record<string, string> = {};
    if (!form.item_name.trim()) validation.item_name = "Item name is required";
    if (!(price > 0)) validation.total_price = "Price must be greater than 0";
    if (!(count >= 1 && count <= MAX_INSTALLMENTS))
      validation.num_installments = `Between 1 and ${MAX_INSTALLMENTS}`;
    if (!(interest >= 0 && interest <= MAX_INTEREST_RATE))
      validation.interest_rate = `Between 0 and ${MAX_INTEREST_RATE}% per month`;
    if (!inputs.purchaseDate) validation.purchase_date = "Required";
    if (!inputs.firstPaymentDate) validation.first_payment_date = "Required";
    setErrors(validation);
    if (Object.keys(validation).length > 0) return;

    setIsSaving(true);
    try {
      await api.createPlan({
        item_name: form.item_name.trim(),
        provider: inputs.provider,
        total_price: price,
        interest_rate: interest,
        num_installments: count,
        purchase_date: inputs.purchaseDate,
        // Only an override is sent; otherwise the backend applies the provider's rule.
        first_payment_date: inputs.firstPaymentOverride || undefined,
      });
      toast("success", "Plan created.");
      onCreated();
      onClose();
    } catch (error) {
      toast("error", error instanceof ApiError ? error.message : "Couldn't create the plan.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Modal isOpen={isOpen} title="Add BNPL plan" onClose={onClose} maxWidth="max-w-2xl">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <TextField
          label="Item name"
          value={form.item_name}
          error={errors.item_name}
          placeholder="e.g. Wireless earbuds"
          onChange={(event) => set("item_name", event.target.value)}
        />
        <SelectField
          label="Provider"
          value={inputs.provider}
          onChange={(event) => inputs.setProvider(event.target.value)}
        >
          {BNPL_PROVIDERS.map((provider) => (
            <option key={provider} value={provider}>
              {provider}
            </option>
          ))}
        </SelectField>
        <CurrencyField
          label="Total price"
          value={form.total_price}
          error={errors.total_price}
          placeholder="0.00"
          onChange={(event) => set("total_price", event.target.value)}
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
        <TextField
          label="Number of instalments"
          type="number"
          min="1"
          max={MAX_INSTALLMENTS}
          value={form.num_installments}
          error={errors.num_installments}
          onChange={(event) => set("num_installments", event.target.value)}
        />
        <DateField
          label="Purchase date"
          value={inputs.purchaseDate}
          error={errors.purchase_date}
          onValueChange={inputs.setPurchaseDate}
        />
        <DateField
          label="First payment date (estimate)"
          hint={firstPaymentHint(inputs.provider)}
          value={inputs.firstPaymentDate}
          error={errors.first_payment_date}
          onValueChange={inputs.setFirstPaymentDate}
        />
      </div>

      {schedule.length > 0 && (
        <div className="mt-4 rounded-lg border border-line bg-surface-2 p-3">
          <div className="mb-2">
            <SchedulePreview schedule={schedule} />
          </div>
          <div className="grid max-h-40 grid-cols-1 gap-1 overflow-y-auto sm:grid-cols-2">
            {schedule.map((item) => (
              <p key={item.seq} className="flex justify-between text-xs text-ink-secondary">
                <span>
                  #{item.seq} · {formatDate(item.dueDate)}
                  {item.paidAtCheckout && (
                    <span className="ml-1.5 text-success">paid at checkout</span>
                  )}
                </span>
                <span className="font-medium text-ink">{formatRM(item.amount)}</span>
              </p>
            ))}
          </div>
        </div>
      )}

      <div className="mt-5 flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button onClick={handleSubmit} disabled={isSaving}>
          {isSaving ? "Creating…" : "Create plan"}
        </Button>
      </div>
    </Modal>
  );
}
