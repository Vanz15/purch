import { createClient } from "@/lib/supabase/client";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

async function authedFetch(
  path: string,
  init: RequestInit = {}
): Promise<any> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string>),
  };
  if (session) {
    headers["Authorization"] = `Bearer ${session.access_token}`;
  }
  const res = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  chat: {
    send: (body: ChatRequest) =>
      authedFetch("/api/chat", { method: "POST", body: JSON.stringify(body) }),
    chooseWallet: (body: { wallet_id: number; pending_wallet: object }) =>
      authedFetch("/api/chat/choose-wallet", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    promptChips: () => authedFetch("/api/chat/prompt-chips"),
  },
  wallets: {
    list: (includeArchived = false) =>
      authedFetch(`/api/wallets?include_archived=${includeArchived}`),
    create: (body: WalletCreate) =>
      authedFetch("/api/wallets", { method: "POST", body: JSON.stringify(body) }),
    update: (id: number, body: WalletUpdate) =>
      authedFetch(`/api/wallets/${id}`, {
        method: "PUT",
        body: JSON.stringify(body),
      }),
    delete: (id: number) =>
      authedFetch(`/api/wallets/${id}`, { method: "DELETE" }),
    archive: (id: number) =>
      authedFetch(`/api/wallets/${id}/archive`, { method: "POST" }),
    restore: (id: number) =>
      authedFetch(`/api/wallets/${id}/restore`, { method: "POST" }),
    summary: () => authedFetch("/api/wallets/summary"),
  },
  analytics: {
    get: (year = 0, month = 0) =>
      authedFetch(`/api/analytics?year=${year}&month=${month}`),
  },
  tone: {
    get: () => authedFetch("/api/tone"),
    set: (tone: string) =>
      authedFetch("/api/tone", {
        method: "POST",
        body: JSON.stringify({ tone }),
      }),
  },
};

// ---- Shared types mirroring the Pydantic models / Reflex TypedDicts ----

export interface ChatMessage {
  role: "user" | "assistant";
  text: string;
  meta: string;
  time: string;
  alert: "" | "warning" | "danger";
}

export interface WalletChoice {
  id: number;
  name: string;
  wallet_type: string;
  balance_display: string;
}

export interface ChatRequest {
  message: string;
  pending_edit?: Record<string, any> | null;
  pending_conversion?: Record<string, any> | null;
  pending_wallet?: Record<string, any> | null;
  wallet_choices?: WalletChoice[] | null;
  awaiting_wallet?: boolean;
}

export interface ChatResponse {
  response: string;
  meta: string;
  alert: "" | "warning" | "danger";
  pending_edit: Record<string, any> | null;
  pending_conversion: Record<string, any> | null;
  pending_wallet: Record<string, any> | null;
  wallet_choices: WalletChoice[];
  awaiting_wallet: boolean;
}

export interface WalletCreate {
  name: string;
  wallet_type: string;
  balance: string;
  note: string;
}

export interface WalletUpdate {
  name: string;
  wallet_type: string;
  balance: string;
  note: string;
}

export interface WalletRow {
  id: number;
  name: string;
  wallet_type: string;
  balance: number;
  balance_display: string;
  note: string;
  is_archived: boolean;
  accent: string;
  pct: number;
  group: string;
}

export interface KpiSnapshot {
  tx_count: number;
  total: number;
}

export interface CategoryRow {
  category: string;
  total: number;
  count: number;
  pct_of_total: number;
}

export interface TrendPoint {
  day: string;
  iso: string;
  total: number;
  count: number;
}

export interface BudgetStatusRow {
  category: string;
  limit_amount: number;
  spent: number;
  pct: number;
  remaining: number;
  status: "on_track" | "near" | "over";
}

export interface RecentTx {
  item: string;
  amount: number;
  category: string;
  tx_timestamp: string;
}

export interface AnalyticsResponse {
  kpi: KpiSnapshot;
  categories: CategoryRow[];
  trend: TrendPoint[];
  trend_peak: number;
  budgets: BudgetStatusRow[];
  budget_used_pct: number;
  budget_limit_total: number;
  budget_spent_total: number;
  recent: RecentTx[];
  top_category: string;
  top_category_amount: number;
  month_label: string;
  unavailable: boolean;
}
