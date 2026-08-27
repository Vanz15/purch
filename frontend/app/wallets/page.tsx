"use client";

import { useEffect, useState, useCallback } from "react";
import { RefreshCw, Plus } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { api, WalletRow, WalletCreate } from "@/lib/api";
import { PageShell, eyebrow, primaryButton, outlineButton } from "@/lib/ui";
import { ChatSidebar } from "@/components/ChatSidebar";
import { isGuest } from "@/lib/guest";

const WALLET_TYPES = ["Cash", "Bank", "Savings", "Debt", "Lent", "Borrowed", "E-wallet", "Investment"];

// Map wallet_type groups to the redesign's Debit/Lent/Borrowed buckets.
function groupOf(wt: string): "Debit" | "Lent" | "Borrowed" {
  if (wt === "Lent") return "Lent";
  if (wt === "Borrowed" || wt === "Debt") return "Borrowed";
  return "Debit";
}
const GROUP_COLOR: Record<string, string> = {
  Debit: "var(--purch-pine)",
  Lent: "var(--purch-gold)",
  Borrowed: "var(--purch-rust)",
};

export default function WalletsPage() {
  const [authed, setAuthed] = useState(false);
  const [rows, setRows] = useState<WalletRow[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [form, setForm] = useState<WalletCreate>({ name: "", wallet_type: "Cash", balance: "", note: "" });
  const [editingId, setEditingId] = useState<number | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [w, s] = await Promise.all([api.wallets.list(true), api.wallets.summary()]);
      setRows(w.wallets || []);
      setSummary(s);
    } catch (e: any) {
      setError(e.message || "Failed to load wallets.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) {
        setAuthed(true);
        load();
      } else if (isGuest()) {
        setAuthed(true);
        load();
      } else {
        setAuthed(false);
      }
    });
  }, [load]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim()) {
      setError("Name is required.");
      return;
    }
    setLoading(true);
    try {
      if (editingId != null) {
        await api.wallets.update(editingId, form);
        setEditingId(null);
      } else {
        await api.wallets.create(form);
      }
      setForm({ name: "", wallet_type: "Cash", balance: "", note: "" });
      setFormOpen(false);
      await load();
    } catch (e: any) {
      setError(e.message || (editingId != null ? "Failed to update wallet." : "Failed to create wallet."));
    } finally {
      setLoading(false);
    }
  }

  async function archive(id: number) {
    setLoading(true);
    try {
      await api.wallets.archive(id);
      await load();
    } finally {
      setLoading(false);
    }
  }
  async function restore(id: number) {
    setLoading(true);
    try {
      await api.wallets.restore(id);
      await load();
    } finally {
      setLoading(false);
    }
  }
  async function remove(id: number) {
    if (!confirm("Delete this wallet permanently?")) return;
    setLoading(true);
    try {
      await api.wallets.delete(id);
      await load();
    } finally {
      setLoading(false);
    }
  }

  if (!authed) {
    return (
      <PageShell active="/wallets" sidebar={<ChatSidebar />}>
        <div className="mx-auto max-w-md">
          <div className="rounded-lg p-8 text-center" style={{ background: "var(--purch-paper)", boxShadow: "var(--purch-shadow-sm)" }}>
            <h1 className="font-['Fraunces'] font-semibold text-3xl m-0 mb-2">Wallets</h1>
            <p className="text-[color:var(--purch-taupe)] text-sm">Sign in to manage your wallets.</p>
            <a href="/" className={`${primaryButton} mt-4`}>Sign in</a>
          </div>
        </div>
      </PageShell>
    );
  }

  if (loading && !rows.length) {
    return (
      <PageShell active="/wallets" sidebar={<ChatSidebar />}>
        <div className="flex flex-col items-center justify-center gap-4 py-24">
          <div
            className="h-10 w-10 rounded-full border-2 border-[color:var(--purch-line)] border-t-[color:var(--purch-pine)] animate-spin"
            role="status"
            aria-label="Loading"
          />
          <p className="font-['Fraunces'] text-[15px] text-[color:var(--purch-taupe)] animate-pulse">
            Counting your coins…
          </p>
        </div>
      </PageShell>
    );
  }

  const active = rows.filter((r) => !r.is_archived);
  const archived = rows.filter((r) => r.is_archived);

  // Build Debit/Lent/Borrowed summary from live wallets.
  const groups: Record<string, { amt: number; pct: number }> = {
    Debit: { amt: 0, pct: 0 },
    Lent: { amt: 0, pct: 0 },
    Borrowed: { amt: 0, pct: 0 },
  };
  for (const r of active) {
    const g = groupOf(r.wallet_type);
    groups[g].amt += r.balance;
  }
  // pct of total magnitude for the progress bars
  const totalMag = Object.values(groups).reduce((s, g) => s + Math.abs(g.amt), 0) || 1;

  return (
    <PageShell active="/wallets" sidebar={<ChatSidebar />}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-6">
        <div>
          <div className={eyebrow}>Money sources</div>
          <h1 className="font-['Fraunces'] font-semibold text-[30px] mt-0 mb-2 m-0">
            Wallets
          </h1>
          <p className="text-[13.5px] text-[color:var(--purch-taupe)] max-w-[480px] leading-relaxed m-0">
            Name each place your money sits. Purch subtracts a purchase from
            whichever wallet you pick in chat.
          </p>
        </div>
        <div className="flex gap-2.5">
          <button onClick={load} disabled={loading} className={`${outlineButton} text-[13px] disabled:opacity-60`}>
            <RefreshCw size={14} /> Refresh
          </button>
          <button onClick={() => { setEditingId(null); setForm({ name: "", wallet_type: "Cash", balance: "", note: "" }); setFormOpen((o) => !o); }} className={`${primaryButton} text-[13px]`}>
            <Plus size={14} /> New wallet
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-3 mb-4 p-3 rounded-lg border" style={{ borderColor: "var(--purch-rust)", background: "var(--purch-paper)" }}>
          <span className="font-bold" style={{ color: "var(--purch-rust)" }}>⚠</span>
          <p className="text-sm flex-1 m-0">{error}</p>
        </div>
      )}

      {/* Net worth / Assets / Liabilities */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5 mb-5">
        <div className="rounded-lg p-5 text-[color:var(--purch-paper)]" style={{ background: "var(--purch-ink)" }}>
          <div className={eyebrow} style={{ color: "var(--purch-taupe)" }}>Net worth</div>
          <div className="font-['JetBrains_Mono'] text-[28px] mt-2" style={{ color: "var(--purch-gold)" }}>
            ₱{summary?.net_display ?? "0.00"}
          </div>
          <div className="text-xs text-[#B8AC9C] mt-1.5">Everything you hold, minus everything you owe.</div>
        </div>
        <div className="rounded-lg p-5 border" style={{ background: "var(--purch-paper)", borderColor: "var(--purch-line)" }}>
          <div className={eyebrow}>Assets</div>
          <div className="font-['JetBrains_Mono'] text-[24px] mt-2" style={{ color: "var(--purch-pine)" }}>
            ₱{summary?.assets_display ?? "0.00"}
          </div>
          <div className="text-xs text-[#B8AC9C] mt-1.5">Cash, bank, savings, and money you've lent out — what you own.</div>
        </div>
        <div className="rounded-lg p-5 border" style={{ background: "var(--purch-paper)", borderColor: "var(--purch-line)" }}>
          <div className={eyebrow}>Liabilities</div>
          <div className="font-['JetBrains_Mono'] text-[24px] mt-2" style={{ color: "var(--purch-rust)" }}>
            ₱{summary?.liabilities_display ?? "0.00"}
          </div>
          <div className="text-xs text-[color:var(--purch-taupe)] mt-1.5">Debts and money you've borrowed — what you owe.</div>
        </div>
      </div>

      {/* Where your money sits */}
      <div className="rounded-lg border p-5 mb-4" style={{ background: "var(--purch-paper)", borderColor: "var(--purch-line)" }}>
        <div className="flex justify-between items-baseline mb-4">
          <h3 className="font-['Fraunces'] font-semibold text-lg m-0">Where your money sits</h3>
          <span className="text-xs text-[color:var(--purch-taupe)]">
            {active.length} active wallet{active.length === 1 ? "" : "s"}
          </span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
          {(["Debit", "Lent", "Borrowed"] as const).map((g) => {
            const pct = Math.round((Math.abs(groups[g].amt) / totalMag) * 100);
            const color = GROUP_COLOR[g];
            const groupWallets = active.filter((w) => groupOf(w.wallet_type) === g);
            const groupTotal = groupWallets.reduce((s, w) => s + w.balance, 0) || 1;
            return (
              <div key={g} className="rounded-md p-4" style={{ background: "var(--purch-bg)" }}>
                <div className="flex justify-between items-center mb-1.5">
                  <span className="font-semibold text-sm">{g}</span>
                  <span className="font-['JetBrains_Mono] text-[13.5px]" style={{ color }}>
                    ₱{groups[g].amt.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                </div>
                <div className="text-[11px] text-[color:var(--purch-taupe)] mb-2.5">
                  {g === "Debit"
                    ? "Bank, cash, savings"
                    : g === "Lent"
                    ? "Money you're waiting on"
                    : "Debt, loan"}
                </div>
                <div className="h-1 rounded-full mb-3" style={{ background: "var(--purch-line)" }}>
                  <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
                </div>
                {/* Per-wallet share of this group (no individual totals — shown above in wallet rows) */}
                <div className="flex flex-col gap-2">
                  {groupWallets.length === 0 ? (
                    <div className="text-[11px] text-[color:var(--purch-taupe)] italic">No {g.toLowerCase()} wallets yet.</div>
                  ) : (
                    groupWallets.map((w) => {
                      const wp = Math.round((w.balance / groupTotal) * 100);
                      return (
                        <div key={w.id}>
                          <div className="flex justify-between text-[11.5px] mb-1">
                            <span className="truncate max-w-[70%]">{w.name}</span>
                            <span className="font-['JetBrains_Mono] text-[color:var(--purch-taupe)]">{wp}%</span>
                          </div>
                          <div className="h-1 rounded-full" style={{ background: "var(--purch-line)" }}>
                            <div className="h-full rounded-full" style={{ width: `${wp}%`, background: color, opacity: 0.55 }} />
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Create form */}
      {formOpen && (
        <form onSubmit={submit} className="rounded-lg border p-5 mb-4" style={{ background: "var(--purch-paper)", borderColor: "var(--purch-line)" }}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-['Fraunces'] font-semibold text-lg m-0">{editingId != null ? "Edit wallet" : "New wallet"}</h3>
            {editingId != null && (
              <button type="button" onClick={() => { setEditingId(null); setForm({ name: "", wallet_type: "Cash", balance: "", note: "" }); setFormOpen(false); }} className="text-xs text-[color:var(--purch-taupe)] hover:text-[color:var(--purch-rust)]">
                Cancel edit
              </button>
            )}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <label className="flex flex-col gap-1">
              <span className={eyebrow}>Name</span>
              <input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                maxLength={40}
                placeholder="e.g. GCash"
                className="rounded-md px-3.5 py-2.5 text-sm bg-[color:var(--purch-paper)]"
                style={{ border: "1px solid var(--purch-line-soft)" }}
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className={eyebrow}>Type</span>
              <select
                value={form.wallet_type}
                onChange={(e) => setForm({ ...form, wallet_type: e.target.value })}
                className="rounded-md px-3.5 py-2.5 text-sm bg-[color:var(--purch-paper)]"
                style={{ border: "1px solid var(--purch-line-soft)" }}
              >
                {WALLET_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <span className={eyebrow}>Starting balance</span>
              <input
                value={form.balance}
                onChange={(e) => setForm({ ...form, balance: e.target.value })}
                placeholder="0.00"
                className="rounded-md px-3.5 py-2.5 text-sm bg-[color:var(--purch-paper)]"
                style={{ border: "1px solid var(--purch-line-soft)" }}
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className={eyebrow}>Note</span>
              <input
                value={form.note}
                onChange={(e) => setForm({ ...form, note: e.target.value })}
                placeholder="optional"
                className="rounded-md px-3.5 py-2.5 text-sm bg-[color:var(--purch-paper)]"
                style={{ border: "1px solid var(--purch-line-soft)" }}
              />
            </label>
          </div>
          <div className="flex gap-2 mt-4">
            <button type="submit" disabled={loading} className={`${primaryButton} text-sm disabled:opacity-60`}>
              {loading ? "Saving…" : editingId != null ? "Save changes" : "Save wallet"}
            </button>
            <button type="button" onClick={() => setFormOpen(false)} className={`${outlineButton} text-sm`}>
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Wallet rows */}
      {active.length === 0 && !loading ? (
        <div className="rounded-lg border p-10 text-center text-[color:var(--purch-taupe)] italic" style={{ background: "var(--purch-paper)", borderColor: "var(--purch-line)" }}>
          No wallets yet — create one to start tracking where your money lives.
        </div>
      ) : (
        <div className="flex flex-col gap-2.5">
          {active.map((w) => (
            <div
              key={w.id}
              className="flex justify-between items-center rounded-lg border px-5 py-4"
              style={{ background: "var(--purch-paper)", borderColor: "var(--purch-line)" }}
            >
              <div>
                <div className="font-semibold text-[15px] mb-0.5">{w.name}</div>
                <span
                  className="text-[11px] px-2 py-0.5 rounded"
                  style={{ background: "#DCEDE6", color: "var(--purch-pine)" }}
                >
                  {w.wallet_type.toUpperCase()}
                </span>
              </div>
              <div className="flex items-center gap-4">
                <span className="font-['JetBrains_Mono'] text-xl">₱{w.balance_display}</span>
                <div className="flex gap-3 text-xs">
                  <button onClick={() => { setForm({ name: w.name, wallet_type: w.wallet_type, balance: String(w.balance), note: w.note ?? "" }); setEditingId(w.id); setFormOpen(true); }} className="text-[color:var(--purch-taupe)] hover:text-[color:var(--purch-pine)] transition-colors">
                    Edit
                  </button>
                  <button onClick={() => archive(w.id)} className="text-[color:var(--purch-taupe)] hover:text-[color:var(--purch-rust)] transition-colors">
                    Archive
                  </button>
                  <button onClick={() => remove(w.id)} className="text-[color:var(--purch-taupe)] hover:text-[color:var(--purch-rust)] transition-colors">
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Archived */}
      {archived.length > 0 && (
        <div className="mt-8">
          <div className={eyebrow}>Archived</div>
          <div className="flex flex-col gap-2.5 mt-2">
            {archived.map((w) => (
              <div
                key={w.id}
                className="flex justify-between items-center rounded-lg border px-5 py-4 opacity-70"
                style={{ background: "var(--purch-paper)", borderColor: "var(--purch-line)" }}
              >
                <div className="font-semibold text-[15px]">{w.name}</div>
                <div className="flex items-center gap-4">
                  <span className="font-['JetBrains_Mono'] text-xl">₱{w.balance_display}</span>
                  <div className="flex gap-3 text-xs">
                    <button onClick={() => restore(w.id)} className="text-[color:var(--purch-taupe)] hover:text-[color:var(--purch-pine)] transition-colors">
                      Restore
                    </button>
                    <button onClick={() => remove(w.id)} className="text-[color:var(--purch-taupe)] hover:text-[color:var(--purch-rust)] transition-colors">
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </PageShell>
  );
}
