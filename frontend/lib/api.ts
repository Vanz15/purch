import { createClient } from "@/lib/supabase/client";
import { getGuestToken, isGuest } from "@/lib/guest";

// Dynamic API URL — always localhost in dev to prevent "failed to fetch".
// NEXT_PUBLIC_API_URL is only used in production.
function resolveApiUrl(): string {
  // SSR / fallback
  if (typeof window === "undefined") return "http://127.0.0.1:8000";
  // Client-side: always derive from the browser origin to avoid stale/dead IPs
  const origin = window.location.origin.replace(":3000", ":8000");
  return origin;
}

async function authedFetch(
  path: string,
  init: RequestInit = {}
): Promise<any> {
  const API_URL = resolveApiUrl();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string>),
  };

  // 1) Prefer a real Supabase session token.
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (session) {
    headers["Authorization"] = `Bearer ${session.access_token}`;
  } else if (isGuest()) {
    // 2) Fall back to a guest JWT minted by the backend (same secret).
    const guestToken = await getGuestToken();
    if (guestToken) {
      headers["Authorization"] = `Bearer ${guestToken}`;
    }
  }

  const res = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (res.status === 401) {
    throw new Error("AUTH_REQUIRED");
  }
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status}`);
  }
  return res.json();
}

// Retry-enabled wrapper — retries failed fetches up to 3 times with backoff
async function retryFetch<T>(
  path: string,
  init: RequestInit = {},
  attempts = 3
): Promise<T> {
  let lastErr: any;
  for (let i = 0; i < attempts; i++) {
    try {
      return await authedFetch(path, init);
    } catch (e: any) {
      lastErr = e;
      // 401 / 403 should not be retried
      if (e.message?.includes("401") || e.message?.includes("403")) {
        throw e;
      }
      if (i < attempts - 1) {
        await new Promise((r) => setTimeout(r, Math.pow(2, i) * 500));
      }
    }
  }
  throw lastErr;
}

export interface WalletRow {
  id: number;
  name: string;
  balance: number;
  balance_display: string;
  wallet_type: string;
  note?: string;
  color?: string;
  is_archived?: boolean;
}

export interface WalletCreate {
  name: string;
  wallet_type: string;
  balance: string;
  note: string;
  color: string;
}

export interface ChatMessage {
  role: "user" | "purch";
  text: string;
  meta?: string;
  is_error?: boolean;
  transaction?: { transaction_id: number; amount: number; item: string };
}

export interface ChatResponse {
  response: string;
  meta?: string;
  is_error?: boolean;
  transaction?: { transaction_id: number; amount: number; item: string };
  tones?: string[];
  action?: string;
  wallet_choices?: WalletRow[];
  pending_wallet?: any;
  pending_conversion?: any;
  pending_edit?: any;
  alert?: any;
}

export interface AnalyticsResponse {
  kpi: { tx_count: number; total: number };
  trend: Array<{ day: string; iso: string; total: number; count: number }>;
  trend_peak: number;
  categories: Array<{ category: string; total: number; count: number; pct_of_total: number }>;
  top_category: string;
  top_category_amount: number;
  budgets: Array<{ category: string; limit_amount: number; spent: number; pct: number; remaining: number; status: string }>;
  budget_used_pct: number;
  budget_limit_total: number;
  budget_spent_total: number;
  recent: Array<{ item: string; amount: number; category: string; tx_timestamp: string }>;
  month_label: string;
  available_months: string[];
  unavailable?: boolean;
}

export interface ToneResponse {
  tone: string;
}

export const api = {
  chat: {
    send: (body: ChatResponse) =>
      retryFetch<ChatResponse>("/api/chat", { method: "POST", body: JSON.stringify(body) }),
    chooseWallet: (body: { wallet_id: number; pending_wallet: object }) =>
      retryFetch("/api/chat/choose-wallet", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    promptChips: () => retryFetch<any>("/api/chat/prompt-chips"),
  },
  wallets: {
    list: (includeArchived = false) =>
      retryFetch<any>(`/api/wallets?include_archived=${includeArchived}`),
    summary: () => retryFetch<any>("/api/wallets/summary"),
    create: (body: WalletCreate) =>
      retryFetch("/api/wallets", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    update: (id: number, body: WalletCreate) =>
      retryFetch(`/api/wallets/${id}`, {
        method: "PUT",
        body: JSON.stringify(body),
      }),
    favorite: (id: number) =>
      retryFetch(`/api/wallets/${id}/favorite`, { method: "POST" }),
    archive: (id: number) =>
      retryFetch(`/api/wallets/${id}/archive`, { method: "POST" }),
    restore: (id: number) =>
      retryFetch(`/api/wallets/${id}/restore`, { method: "POST" }),
    delete: (id: number) =>
      retryFetch(`/api/wallets/${id}`, { method: "DELETE" }),
  },
  transactions: {
    list: (opts: { category?: string | null; q?: string | null; limit?: number } = {}) => {
      const params = new URLSearchParams();
      if (opts.category) params.set("category", opts.category);
      if (opts.q) params.set("q", opts.q);
      if (opts.limit) params.set("limit", String(opts.limit));
      const qs = params.toString();
      return retryFetch<any>(`/api/transactions${qs ? `?${qs}` : ""}`);
    },
    update: (id: number, body: { item?: string; amount?: number; category?: string }) =>
      retryFetch(`/api/transactions/${id}`, {
        method: "PUT",
        body: JSON.stringify(body),
      }),
    delete: (id: number) =>
      retryFetch(`/api/transactions/${id}`, { method: "DELETE" }),
  },
  analytics: {
    get: (year: number, month: number) =>
      retryFetch<AnalyticsResponse>(`/api/analytics?year=${year}&month=${month}`),
    months: () => retryFetch<AnalyticsResponse>(`/api/analytics?year=0&month=0`),
  },
  tone: {
    get: () => retryFetch<ToneResponse>("/api/tone"),
    set: (tone: string) =>
      retryFetch("/api/tone", {
        method: "POST",
        body: JSON.stringify({ tone }),
      }),
  },
};
