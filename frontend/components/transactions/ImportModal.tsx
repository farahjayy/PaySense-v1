"use client";
// CSV/PDF import flow: dropzone → preview (editable) → confirm → toast.
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { FileDropzone } from "@/components/ui/FileDropzone";
import { Modal } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";
import { api, ApiError } from "@/lib/api";
import { TRANSACTION_CATEGORIES } from "@/lib/constants";
import { formatDate, formatRM } from "@/lib/format";
import type { ImportPreview, ImportRow } from "@/lib/types";

type Props = {
  isOpen: boolean;
  kind: "csv" | "pdf";
  onClose: () => void;
  onImported: () => void;
};

type Stage = "pick" | "uploading" | "preview" | "confirming";

export function ImportModal({ isOpen, kind, onClose, onImported }: Props) {
  const toast = useToast();
  const [stage, setStage] = useState<Stage>("pick");
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [rows, setRows] = useState<ImportRow[]>([]);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const reset = () => {
    setStage("pick");
    setPreview(null);
    setRows([]);
    setUploadError(null);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleFile = async (file: File) => {
    setStage("uploading");
    setUploadError(null);
    try {
      const result = await api.importFile(kind, file);
      setPreview(result);
      setRows(result.rows);
      setStage("preview");
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : "Couldn't parse this file — try again.";
      const hint =
        error instanceof ApiError && error.code === "PDF_PARSE_FAILED"
          ? " Most banks let you download a CSV from the same page."
          : "";
      setUploadError(message + hint);
      setStage("pick");
    }
  };

  const updateRow = (index: number, patch: Partial<ImportRow>) => {
    setRows((current) => current.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  };

  const removeRow = (index: number) => {
    setRows((current) => current.filter((_, i) => i !== index));
  };

  const handleConfirm = async () => {
    if (!preview) return;
    setStage("confirming");
    try {
      const result = await api.importConfirm(preview.import_id, rows);
      toast("success", `Imported ${result.inserted} transactions.`);
      onImported();
      handleClose();
    } catch (error) {
      toast("error", error instanceof ApiError ? error.message : "Import failed — try again.");
      setStage("preview");
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      title={`Import ${kind.toUpperCase()} statement`}
      onClose={handleClose}
      maxWidth="max-w-3xl"
    >
      {stage === "pick" && (
        <div className="flex flex-col gap-3">
          {uploadError && (
            <p role="alert" className="rounded-lg border border-danger/30 bg-danger-bg px-3 py-2 text-[13px] font-medium text-danger">
              {uploadError}
            </p>
          )}
          <FileDropzone
            accept={kind === "csv" ? ".csv" : ".pdf"}
            hint={
              kind === "csv"
                ? "CSV with date, description and amount columns · max 5 MB"
                : "Maybank / CIMB / RHB statement PDF · max 5 MB"
            }
            onFile={handleFile}
          />
        </div>
      )}

      {stage === "uploading" && (
        <div className="flex flex-col items-center gap-3 py-10">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-line border-t-accent" />
          <p className="text-[13px] text-ink-secondary">Reading your statement…</p>
        </div>
      )}

      {(stage === "preview" || stage === "confirming") && preview && (
        <div className="flex flex-col gap-3">
          <p className="text-[13px] text-ink-secondary">
            Review before importing — fix categories or remove rows you don&apos;t want.
          </p>
          <div className="max-h-[45vh] overflow-auto rounded-lg border border-line">
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 bg-surface-2">
                <tr className="text-[11px] text-ink-secondary">
                  <th className="px-3 py-2 font-semibold">Date</th>
                  <th className="px-3 py-2 font-semibold">Description</th>
                  <th className="px-3 py-2 font-semibold">Type</th>
                  <th className="px-3 py-2 font-semibold">Category</th>
                  <th className="px-3 py-2 text-right font-semibold">Amount</th>
                  <th className="px-2 py-2" />
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {rows.map((row, index) => (
                  <tr key={row.row} className={row.issues.length > 0 ? "bg-warning-bg/50" : ""}>
                    <td className="whitespace-nowrap px-3 py-1.5">{formatDate(row.date)}</td>
                    <td className="max-w-[220px] px-3 py-1.5">
                      <p className="truncate">{row.description ?? "—"}</p>
                      {row.issues.map((issue) => (
                        <p key={issue} className="text-[10px] font-medium text-warning">
                          ⚠ {issue}
                        </p>
                      ))}
                    </td>
                    <td className="px-3 py-1.5">
                      <select
                        value={row.type}
                        aria-label={`Type for row ${row.row}`}
                        onChange={(event) =>
                          updateRow(index, { type: event.target.value as ImportRow["type"] })
                        }
                        className="rounded border border-line bg-surface px-1.5 py-1 text-xs"
                      >
                        <option value="expense">expense</option>
                        <option value="income">income</option>
                      </select>
                    </td>
                    <td className="px-3 py-1.5">
                      <select
                        value={row.category_guess}
                        aria-label={`Category for row ${row.row}`}
                        onChange={(event) => updateRow(index, { category_guess: event.target.value })}
                        className="rounded border border-line bg-surface px-1.5 py-1 text-xs"
                      >
                        {!TRANSACTION_CATEGORIES.includes(
                          row.category_guess as (typeof TRANSACTION_CATEGORIES)[number],
                        ) && <option value={row.category_guess}>{row.category_guess}</option>}
                        {TRANSACTION_CATEGORIES.map((category) => (
                          <option key={category} value={category}>
                            {category}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td
                      className={`whitespace-nowrap px-3 py-1.5 text-right font-semibold ${
                        row.type === "income" ? "text-success" : "text-danger"
                      }`}
                    >
                      {row.type === "income" ? "+" : "−"}
                      {formatRM(row.amount)}
                    </td>
                    <td className="px-2 py-1.5">
                      <button
                        type="button"
                        aria-label={`Remove row ${row.row}`}
                        onClick={() => removeRow(index)}
                        className="rounded px-1.5 text-ink-muted hover:bg-danger-bg hover:text-danger"
                      >
                        ×
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {preview.skipped.length > 0 && (
            <details className="rounded-lg border border-line bg-surface-2 px-3 py-2 text-xs text-ink-secondary">
              <summary className="cursor-pointer font-semibold">
                {preview.skipped.length} row{preview.skipped.length > 1 ? "s" : ""} skipped
              </summary>
              <ul className="mt-1.5 list-inside list-disc">
                {preview.skipped.map((skip) => (
                  <li key={skip.row}>
                    Row {skip.row}: {skip.reason}
                  </li>
                ))}
              </ul>
            </details>
          )}

          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={handleClose}>
              Cancel
            </Button>
            <Button onClick={handleConfirm} disabled={stage === "confirming" || rows.length === 0}>
              {stage === "confirming"
                ? "Importing…"
                : `Import ${rows.length} transaction${rows.length === 1 ? "" : "s"}`}
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
}
