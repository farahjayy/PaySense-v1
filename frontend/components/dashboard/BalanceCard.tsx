"use client";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useToast } from "@/components/ui/Toast";
import { api, ApiError } from "@/lib/api";
import { formatRM, relativeTime } from "@/lib/format";

type Props = {
  balance: number;
  syncedAt: string;
  onSynced: () => void;
};

export function BalanceCard({ balance, syncedAt, onSynced }: Props) {
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const toast = useToast();

  const handleSave = async () => {
    const value = Number(draft);
    if (!Number.isFinite(value)) {
      toast("error", "Enter a valid balance amount.");
      return;
    }
    setIsSaving(true);
    try {
      await api.updateBalance(value);
      toast("success", "Balance synced.");
      setIsEditing(false);
      onSynced();
    } catch (error) {
      toast("error", error instanceof ApiError ? error.message : "Couldn't update the balance.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Card className="flex flex-col justify-between gap-3">
      <div>
        <p className="text-xs font-medium text-ink-secondary">Current Balance</p>
        {isEditing ? (
          <div className="mt-2 flex items-center gap-2">
            <div className="relative">
              <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-ink-muted">
                RM
              </span>
              <input
                autoFocus
                type="number"
                step="0.01"
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => event.key === "Enter" && handleSave()}
                className="h-10 w-40 rounded-lg border border-line pl-10 pr-2 text-lg font-semibold"
                aria-label="New balance"
              />
            </div>
            <Button size="sm" onClick={handleSave} disabled={isSaving}>
              {isSaving ? "Saving…" : "Save"}
            </Button>
            <Button size="sm" variant="secondary" onClick={() => setIsEditing(false)}>
              Cancel
            </Button>
          </div>
        ) : (
          <p className="mt-1 text-3xl font-bold tracking-tight text-ink">{formatRM(balance)}</p>
        )}
      </div>
      <div className="flex items-center justify-between">
        <p className="text-[11px] text-ink-muted">synced {relativeTime(syncedAt)}</p>
        {!isEditing && (
          <Button
            size="sm"
            variant="secondary"
            onClick={() => {
              setDraft(String(balance));
              setIsEditing(true);
            }}
          >
            Sync
          </Button>
        )}
      </div>
    </Card>
  );
}
