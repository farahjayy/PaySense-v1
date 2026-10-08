"use client";
// Transactions: toolbar filters, paginated table, category breakdown, import flow.
import { useState } from "react";

import { ImportModal } from "@/components/transactions/ImportModal";
import { TransactionModal } from "@/components/transactions/TransactionModal";
import { Button } from "@/components/ui/Button";
import { Card, CardCaption, CardTitle } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { CardSkeleton, EmptyState, ErrorBanner, Skeleton } from "@/components/ui/States";
import { useToast } from "@/components/ui/Toast";
import { api, ApiError } from "@/lib/api";
import { currentMonth, formatDate, formatRM } from "@/lib/format";
import type { MonthSummary, Transaction, TransactionList } from "@/lib/types";
import { useApi } from "@/lib/useApi";

const PAGE_SIZE = 25;

export default function TransactionsPage() {
  const toast = useToast();
  const [month, setMonth] = useState(currentMonth());
  const [category, setCategory] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [modal, setModal] = useState<"none" | "form" | "import-csv" | "import-pdf">("none");
  const [editing, setEditing] = useState<Transaction | null>(null);

  const list = useApi<TransactionList>(
    () =>
      api.transactions({
        month: month || undefined,
        category: category || undefined,
        type: typeFilter || undefined,
        search: search || undefined,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      }),
    [month, category, typeFilter, search, page],
  );
  const summary = useApi<MonthSummary>(() => api.transactionSummary(month), [month]);

  const refetchAll = () => {
    list.refetch();
    summary.refetch();
  };

  const handleDelete = async (transaction: Transaction) => {
    if (!window.confirm(`Delete "${transaction.description ?? transaction.category}" (${formatRM(transaction.amount)})?`)) {
      return;
    }
    try {
      await api.deleteTransaction(transaction.id);
      toast("success", "Transaction deleted.");
      refetchAll();
    } catch (error) {
      toast("error", error instanceof ApiError ? error.message : "Couldn't delete the transaction.");
    }
  };

  const totalPages = list.data ? Math.max(1, Math.ceil(list.data.total / PAGE_SIZE)) : 1;
  const categories = summary.data?.by_category.map((entry) => entry.category) ?? [];

  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-ink">Transactions</h1>
          <p className="text-[13px] text-ink-secondary">Every ringgit in and out</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => setModal("import-csv")}>
            Import CSV
          </Button>
          <Button variant="secondary" onClick={() => setModal("import-pdf")}>
            Import PDF
          </Button>
          <Button
            onClick={() => {
              setEditing(null);
              setModal("form");
            }}
          >
            + Add transaction
          </Button>
        </div>
      </header>

      <Card className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-secondary">
          Month
          <input
            type="month"
            value={month}
            onChange={(event) => {
              setMonth(event.target.value);
              setPage(0);
            }}
            className="h-9 rounded-lg border border-line bg-surface px-3 text-[13px] text-ink"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-secondary">
          Category
          <select
            value={category}
            onChange={(event) => {
              setCategory(event.target.value);
              setPage(0);
            }}
            className="h-9 rounded-lg border border-line bg-surface px-3 text-[13px] text-ink"
          >
            <option value="">All categories</option>
            {categories.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
        <div className="flex flex-col gap-1 text-xs font-medium text-ink-secondary">
          Type
          <div className="flex overflow-hidden rounded-lg border border-line" role="group" aria-label="Type filter">
            {[
              ["", "All"],
              ["income", "Income"],
              ["expense", "Expense"],
              ["savings", "Savings"],
            ].map(([value, label]) => (
              <button
                key={value}
                type="button"
                onClick={() => {
                  setTypeFilter(value);
                  setPage(0);
                }}
                className={`h-9 px-3 text-[13px] font-medium transition-colors ${
                  typeFilter === value ? "bg-accent-bg text-accent" : "bg-surface text-ink-secondary hover:bg-surface-2"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
        <label className="flex min-w-40 flex-1 flex-col gap-1 text-xs font-medium text-ink-secondary">
          Search
          <input
            type="search"
            placeholder="e.g. grab, mamak…"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(0);
            }}
            className="h-9 rounded-lg border border-line bg-surface px-3 text-[13px] text-ink placeholder:text-ink-muted"
          />
        </label>
      </Card>

      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <Card>
          {list.error && <ErrorBanner message={list.error} onRetry={list.refetch} />}
          {list.isLoading && (
            <div className="flex flex-col gap-2">
              {Array.from({ length: 8 }, (_, i) => (
                <Skeleton key={i} className="h-9 w-full" />
              ))}
            </div>
          )}
          {list.data && !list.isLoading && list.data.items.length === 0 && (
            <EmptyState
              icon="🧾"
              message="No transactions match — add your first transaction or import a bank statement."
              action={
                <Button
                  size="sm"
                  onClick={() => {
                    setEditing(null);
                    setModal("form");
                  }}
                >
                  + Add transaction
                </Button>
              }
            />
          )}
          {list.data && !list.isLoading && list.data.items.length > 0 && (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-[13px]">
                  <thead>
                    <tr className="border-b border-line text-[11px] text-ink-secondary">
                      <th className="py-2 pr-3 font-semibold">Date</th>
                      <th className="py-2 pr-3 font-semibold">Description</th>
                      <th className="py-2 pr-3 font-semibold">Category</th>
                      <th className="hidden py-2 pr-3 font-semibold sm:table-cell">Account</th>
                      <th className="py-2 pr-3 text-right font-semibold">Amount</th>
                      <th className="py-2" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {list.data.items.map((transaction) => (
                      <tr key={transaction.id} className="group hover:bg-surface-2">
                        <td className="whitespace-nowrap py-2.5 pr-3 text-ink-secondary">
                          {formatDate(transaction.date)}
                        </td>
                        <td className="max-w-[260px] py-2.5 pr-3 font-medium text-ink">
                          <div className="flex items-center gap-1.5">
                            <span className="truncate" title={transaction.description ?? undefined}>
                              {transaction.description ?? "—"}
                            </span>
                            {transaction.is_bnpl && (
                              <span className="shrink-0">
                                <Chip tone="accent">BNPL</Chip>
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-2.5 pr-3">
                          <Chip tone="neutral">{transaction.category}</Chip>
                        </td>
                        <td className="hidden py-2.5 pr-3 text-ink-muted sm:table-cell">
                          {transaction.account_name ?? "—"}
                        </td>
                        <td
                          className={`whitespace-nowrap py-2.5 pr-3 text-right font-semibold ${
                            transaction.type === "income" ? "text-success" : "text-danger"
                          }`}
                        >
                          {transaction.type === "income" ? "+" : "−"}
                          {formatRM(transaction.amount)}
                        </td>
                        <td className="py-2.5 text-right">
                          <div className="flex justify-end gap-1 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
                            <button
                              type="button"
                              aria-label="Edit transaction"
                              onClick={() => {
                                setEditing(transaction);
                                setModal("form");
                              }}
                              className="rounded px-1.5 py-0.5 text-xs text-ink-secondary hover:bg-accent-bg hover:text-accent"
                            >
                              Edit
                            </button>
                            <button
                              type="button"
                              aria-label="Delete transaction"
                              onClick={() => handleDelete(transaction)}
                              className="rounded px-1.5 py-0.5 text-xs text-ink-secondary hover:bg-danger-bg hover:text-danger"
                            >
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="mt-3 flex items-center justify-between text-xs text-ink-secondary">
                <span>
                  {list.data.total} transaction{list.data.total === 1 ? "" : "s"}
                </span>
                <div className="flex items-center gap-2">
                  <Button size="sm" variant="secondary" disabled={page === 0} onClick={() => setPage(page - 1)}>
                    ← Prev
                  </Button>
                  <span>
                    Page {page + 1} of {totalPages}
                  </span>
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={page + 1 >= totalPages}
                    onClick={() => setPage(page + 1)}
                  >
                    Next →
                  </Button>
                </div>
              </div>
            </>
          )}
        </Card>

        <Card className="h-fit">
          <CardTitle>Spending by category</CardTitle>
          <CardCaption>{month}</CardCaption>
          {summary.isLoading && <CardSkeleton lines={5} />}
          {summary.error && <ErrorBanner message={summary.error} onRetry={summary.refetch} />}
          {summary.data && !summary.isLoading && (
            <div className="mt-3 flex flex-col gap-2.5">
              {summary.data.by_category.length === 0 && (
                <EmptyState icon="📊" message="No spending recorded this month yet." />
              )}
              {summary.data.by_category.map((entry) => (
                <div key={entry.category}>
                  <div className="mb-1 flex items-baseline justify-between text-xs">
                    <span className="font-medium text-ink">{entry.category}</span>
                    <span className="text-ink-secondary">
                      {formatRM(entry.total)} · {entry.pct}%
                    </span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-line/60">
                    <div
                      className="h-full rounded-full bg-accent"
                      style={{ width: `${Math.min(100, entry.pct)}%` }}
                    />
                  </div>
                </div>
              ))}
              {summary.data.by_category.length > 0 && (
                <p className="mt-1 border-t border-line pt-2 text-xs text-ink-secondary">
                  Income {formatRM(summary.data.income)} · Spent {formatRM(summary.data.expenses)}
                </p>
              )}
            </div>
          )}
        </Card>
      </div>

      <TransactionModal
        isOpen={modal === "form"}
        editing={editing}
        onClose={() => setModal("none")}
        onSaved={refetchAll}
      />
      <ImportModal
        isOpen={modal === "import-csv" || modal === "import-pdf"}
        kind={modal === "import-pdf" ? "pdf" : "csv"}
        onClose={() => setModal("none")}
        onImported={refetchAll}
      />
    </div>
  );
}
