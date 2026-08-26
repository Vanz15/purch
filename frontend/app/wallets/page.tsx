"use client";

import { useEffect, useState, useCallback } from "react";
import { createClient } from "@/lib/supabase/client";
import { api, WalletRow, WalletCreate } from "@/lib/api";
import { PageShell, eyebrow, primaryButton, outlineButton } from "@/lib/ui";

const WALLET_TYPES = ["Cash", "Bank", "Savings", "Debt", "Lent", "Borrowed", "E-wallet", "Investment"];

export default function WalletsPage() {
  const [authed, setAuthed] = useState(false);
  const [rows, setRows] = useState<WalletRow[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [form, setForm] = useState<WalletCreate>({ name: "", wallet_type: "Cash", balance: "", note: "" });
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
      if (!data.session) {
        setAuthed(false);
      } else {
        setAuthed(true);
        load();
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
      await api.wallets.create(form);
      setForm({ name: "", wallet_type: "Cash", balance: "", note: "" });
      setFormOpen(false);
      await load();
    } catch (e: any) {
      setError(e.message || "Failed to create wallet.");
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
      <PageShell active="/wallets">
        <div className="max-w-6xl mx-auto w-full p-6">
          <div className="purch-card p-8 text-center">
            <h1 className="font-['Playfair_Display'] font-bold text-3xl text-[color:var(--purch-ink)]">
              Wallets
            </h1>
            <p className="text-[color:var(--purch-secondary-text)] mt-2">
              Sign in to manage your wallets.
            </p>
            <a href="/login" className={`${primaryButton} mt-4`}>
              Sign in
            </a>
          </div>
        </div>
      </PageShell>
    );
  }

  const active = rows.filter((r) => !r.is_archived);
  const archived = rows.filter((r) => r.is_archived);

  return (
    <PageShell active="/wallets">
      <div className="max-w-6xl mx-auto w-full p-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3 mb-6">
          <div className="flex-1 min-w-0">
            <div className={eyebrow}>Money sources</div>
            <h1 className="font-['Playfair_Display'] font-bold tracking-tight text-3xl sm:text-4xl text-[color:var(--purch-ink)] mt-1">
              Wallets
            </h1>
            <p className="text-sm text-[color:var(--purch-secondary-text)] mt-2 max-w-xl">
              Nickname each place your money sits, and see your net worth,
              assets, and liabilities at a glance. Purch subtracts a purchase
              from the wallet you pick in chat.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={load}
              disabled={loading}
              className={`${outlineButton} text-sm disabled:opacity-60`}
            >
              {loading ? "Refreshing…" : "↻ Refresh"}
            </button>
            <button
              onClick={() => setFormOpen((o) => !o)}
              className={`${primaryButton} text-sm`}
            >
              + New wallet
            </button>
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-3 mb-4 p-3 rounded-xl border border-[color:var(--purch-danger)] bg-[color:var(--purch-paper)]">
            <span className="text-[color:var(--purch-danger)] font-bold">⚠</span>
            <p className="text-sm flex-1 m-0">{error}</p>
          </div>
        )}

        {/* Summary */}
        {summary && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            {[
              { label: "Net worth", value: summary.net_display, tone: "ink" },
              { label: "Assets", value: summary.assets_display, tone: "teal" },
              { label: "Liabilities", value: summary.liabilities_display, tone: "danger" },
              { label: "Debit total", value: summary.debit_total_display, tone: "ink" },
            ].map((k) => (
              <div key={k.label} className="purch-card p-5">
                <div className={eyebrow}>{k.label}</div>
                <div
                  className={
                    "font-['Playfair_Display'] font-bold text-3xl mt-2 " +
                    (k.tone === "teal"
                      ? "text-[color:var(--purch-teal)]"
                      : k.tone === "danger"
                      ? "text-[color:var(--purch-danger)]"
                      : "text-[color:var(--purch-ink)]")
                  }
                >
                  ₱{k.value}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Form */}
        {formOpen && (
          <form onSubmit={submit} className="purch-card p-6 mb-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <label className="flex flex-col gap-1">
                <span className={eyebrow}>Name</span>
                <input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  maxLength={40}
                  placeholder="e.g. GCash"
                  className="rounded-xl border border-[color:var(--purch-border)] bg-[color:var(--purch-paper)] px-3.5 py-2.5 text-sm focus:outline-none focus:border-[color:var(--purch-coral)]"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className={eyebrow}>Type</span>
                <select
                  value={form.wallet_type}
                  onChange={(e) => setForm({ ...form, wallet_type: e.target.value })}
                  className="rounded-xl border border-[color:var(--purch-border)] bg-[color:var(--purch-paper)] px-3.5 py-2.5 text-sm focus:outline-none focus:border-[color:var(--purch-coral)]"
                >
                  {WALLET_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-1">
                <span className={eyebrow}>Starting balance</span>
                <input
                  value={form.balance}
                  onChange={(e) => setForm({ ...form, balance: e.target.value })}
                  placeholder="0.00"
                  className="rounded-xl border border-[color:var(--purch-border)] bg-[color:var(--purch-paper)] px-3.5 py-2.5 text-sm focus:outline-none focus:border-[color:var(--purch-coral)]"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className={eyebrow}>Note</span>
                <input
                  value={form.note}
                  onChange={(e) => setForm({ ...form, note: e.target.value })}
                  placeholder="optional"
                  className="rounded-xl border border-[color:var(--purch-border)] bg-[color:var(--purch-paper)] px-3.5 py-2.5 text-sm focus:outline-none focus:border-[color:var(--purch-coral)]"
                />
              </label>
            </div>
            <div className="flex gap-2 mt-4">
              <button type="submit" disabled={loading} className={`${primaryButton} text-sm disabled:opacity-60`}>
                {loading ? "Saving…" : "Save wallet"}
              </button>
              <button type="button" onClick={() => setFormOpen(false)} className={`${outlineButton} text-sm`}>
                Cancel
              </button>
            </div>
          </form>
        )}

        {/* Wallet grid */}
        {active.length === 0 && !loading ? (
          <div className="purch-card p-10 text-center text-[color:var(--purch-muted)] italic">
            No wallets yet — create one to start tracking where your money lives.
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {active.map((w) => (
              <div key={w.id} className="purch-card p-5">
                <div className="flex items-center justify-between gap-2 mb-3">
                  <h3 className="font-['Playfair_Display'] font-bold text-lg text-[color:var(--purch-ink)] m-0">
                    {w.name}
                  </h3>
                  <span className="purch-chip">{w.wallet_type}</span>
                </div>
                <div className="font-['DM_Mono'] text-2xl font-bold text-[color:var(--purch-ink)]">
                  ₱{w.balance_display}
                </div>
                {w.note && (
                  <p className="text-xs text-[color:var(--purch-muted)] mt-2">{w.note}</p>
                )}
                <div className="flex gap-3 mt-4 text-xs">
                  <button onClick={() => archive(w.id)} className="text-[color:var(--purch-muted)] hover:text-[color:var(--purch-coral)] transition-colors">
                    Archive
                  </button>
                  <button onClick={() => remove(w.id)} className="text-[color:var(--purch-muted)] hover:text-[color:var(--purch-danger)] transition-colors">
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Archived */}
        {archived.length > 0 && (
          <div className="mt-8">
            <div className={eyebrow}>Archived</div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-2">
              {archived.map((w) => (
                <div key={w.id} className="purch-card p-5 opacity-70">
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <h3 className="font-['Playfair_Display'] font-bold text-lg text-[color:var(--purch-ink)] m-0">
                      {w.name}
                    </h3>
                    <span className="purch-chip">{w.wallet_type}</span>
                  </div>
                  <div className="font-['DM_Mono'] text-2xl font-bold text-[color:var(--purch-ink)]">
                    ₱{w.balance_display}
                  </div>
                  <div className="flex gap-3 mt-4 text-xs">
                    <button onClick={() => restore(w.id)} className="text-[color:var(--purch-muted)] hover:text-[color:var(--purch-teal)] transition-colors">
                      Restore
                    </button>
                    <button onClick={() => remove(w.id)} className="text-[color:var(--purch-muted)] hover:text-[color:var(--purch-danger)] transition-colors">
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </PageShell>
  );
}
