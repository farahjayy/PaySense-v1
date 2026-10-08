"use client";
// Rename a plan. The item name is the only editable field: it is cosmetic, so it can change at
// any time (even after instalments are paid) with no effect on amounts, dates or the balance.
// To change price, fee, instalments or dates, delete the plan and create a new one.
// Mounted only while open, so it always starts from the plan's current name.
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";
import { TextField } from "@/components/ui/fields";
import { api, ApiError } from "@/lib/api";
import type { Plan } from "@/lib/types";

type Props = {
  plan: Plan;
  onClose: () => void;
  onSaved: () => void;
};

export function RenamePlanModal({ plan, onClose, onSaved }: Props) {
  const toast = useToast();
  const [name, setName] = useState(plan.item_name);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async () => {
    const trimmed = name.trim();
    if (!trimmed) {
      setError("Item name is required");
      return;
    }
    if (trimmed === plan.item_name) {
      onClose();
      return;
    }
    setIsSaving(true);
    try {
      await api.updatePlan(plan.id, { item_name: trimmed });
      toast("success", "Plan renamed.");
      onSaved();
      onClose();
    } catch (err) {
      toast("error", err instanceof ApiError ? err.message : "Couldn't rename the plan.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Modal isOpen title="Rename plan" onClose={onClose}>
      <TextField
        label="Item name"
        value={name}
        error={error}
        onChange={(event) => setName(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter") void handleSave();
        }}
        autoFocus
      />
      <p className="mt-2 text-[11px] text-ink-muted">
        Only the name can be changed. To change the price, fee, instalments or dates, delete this plan and
        create a new one. Transactions this plan logged are renamed to match.
      </p>
      <div className="mt-5 flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button onClick={handleSave} disabled={isSaving}>
          {isSaving ? "Saving…" : "Save"}
        </Button>
      </div>
    </Modal>
  );
}
