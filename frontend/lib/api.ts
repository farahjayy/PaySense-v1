// Single typed fetch layer — every API call goes through here so errors are
// normalised once and screens can always show a readable message.
import type {
  Balance,
  Bills,
  Dashboard,
  Forecast,
  ImportPreview,
  ImportRow,
  MonthSummary,
  DeletePlanResult,
  Plan,
  PlanInput,
  PlanTransactions,
  PlanUpdateInput,
  RiskReport,
  Profile,
  RiskCheckInput,
  RiskCheckResult,
  Transaction,
  TransactionInput,
  TransactionList,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, init);
  } catch {
    throw new ApiError(0, "NETWORK_ERROR", "Can't reach the PaySense server — is the backend running?");
  }

  if (!response.ok) {
    let code = "UNKNOWN_ERROR";
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (body?.detail && typeof body.detail === "object") {
        code = body.detail.code ?? code;
        message = body.detail.message ?? message;
      } else if (typeof body?.detail === "string") {
        message = body.detail;
      }
    } catch {
      // Non-JSON error body: keep the generic message.
    }
    throw new ApiError(response.status, code, message);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function jsonInit(method: string, body: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

export const api = {
  dashboard: () => request<Dashboard>("/api/dashboard"),
  bills: () => request<Bills>("/api/bnpl/bills"),

  balance: () => request<Balance>("/api/balance"),
  updateBalance: (currentBalance: number) =>
    request<Balance>("/api/balance", jsonInit("PUT", { current_balance: currentBalance })),

  profile: () => request<Profile>("/api/profile"),
  updateProfile: (profile: Profile) => request<Profile>("/api/profile", jsonInit("PUT", profile)),

  transactions: (params: {
    month?: string;
    category?: string;
    type?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }) => {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== "") query.set(key, String(value));
    }
    return request<TransactionList>(`/api/transactions?${query.toString()}`);
  },
  createTransaction: (input: TransactionInput) =>
    request<Transaction>("/api/transactions", jsonInit("POST", input)),
  updateTransaction: (id: string, input: Partial<TransactionInput>) =>
    request<Transaction>(`/api/transactions/${id}`, jsonInit("PUT", input)),
  deleteTransaction: (id: string) => request<void>(`/api/transactions/${id}`, { method: "DELETE" }),
  transactionSummary: (month: string) =>
    request<MonthSummary>(`/api/transactions/summary?month=${month}`),

  plans: (status?: string) =>
    request<Plan[]>(`/api/bnpl/plans${status ? `?status=${status}` : ""}`),
  createPlan: (input: PlanInput) => request<Plan>("/api/bnpl/plans", jsonInit("POST", input)),
  plan: (id: string) => request<Plan>(`/api/bnpl/plans/${id}`),
  payInstallment: (planId: string, seq: number, createTransaction = true) =>
    request<Plan>(
      `/api/bnpl/plans/${planId}/installments/${seq}/pay`,
      jsonInit("POST", { create_transaction: createTransaction }),
    ),
  updatePlan: (id: string, input: PlanUpdateInput) =>
    request<Plan>(`/api/bnpl/plans/${id}`, jsonInit("PATCH", input)),
  planRiskReport: (id: string) => request<RiskReport>(`/api/bnpl/plans/${id}/risk-report`),
  planTransactions: (id: string) => request<PlanTransactions>(`/api/bnpl/plans/${id}/transactions`),
  // Transactions are kept unless deleteTransactions is explicitly true.
  deletePlan: (id: string, deleteTransactions = false) =>
    request<DeletePlanResult>(`/api/bnpl/plans/${id}?delete_transactions=${deleteTransactions}`, {
      method: "DELETE",
    }),

  forecast: () => request<Forecast>("/api/forecast"),
  riskCheck: (input: RiskCheckInput) =>
    request<RiskCheckResult>("/api/risk/check", jsonInit("POST", input)),
  riskConfirm: (checkId: string) =>
    request<Plan>("/api/risk/confirm", jsonInit("POST", { check_id: checkId })),

  importFile: (kind: "csv" | "pdf", file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<ImportPreview>(`/api/import/${kind}`, { method: "POST", body: form });
  },
  importConfirm: (importId: string, rows: ImportRow[]) =>
    request<{ inserted: number }>("/api/import/confirm", jsonInit("POST", { import_id: importId, rows })),
};
