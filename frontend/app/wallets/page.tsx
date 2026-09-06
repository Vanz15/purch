"use client";

import { useEffect, useState, useCallback } from "react";
import { RefreshCw, Plus, Star } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { api, WalletRow, WalletCreate } from "@/lib/api";
import { PageShell, eyebrow, primaryButton, outlineButton, useToast } from "@/lib/ui";
import { isGuest } from "@/lib/guest";
import { loadFavorites, saveFavorites, toggleFavorite as toggleFav } from "@/components/WalletStrip";

const MAX_FAVORITES = 3;

/** Try to add id to favorites. Returns true on success, false if limit hit. */
function tryAddFavorite(id: number, rows: WalletRow[]): boolean {
  const favs = loadFavorites();
  if (favs.has(id)) {
    // Already a favorite — just toggle off
    toggleFav(id);
    return true;
  }
  if (favs.size >= MAX_FAVORITES) {
    return false; // limit reached
  }
  toggleFav(id);
  return true;
}

/** Build a user-facing message listing the current favorite wallet names. */
function favoriteLimitMessage(rows: WalletRow[]): string {
  const favs = loadFavorites();
  const names = rows.filter((w) => favs.has(w.id)).map((w) => w.name);
  return `You can only favorite ${MAX_FAVORITES} wallets. Currently: ${names.join(", ")}. Remove one first.`;
}

const WALLET_TYPES = ["Cash", "Bank", "Savings", "Debt", "Lent", "Borrowed", "E-wallet", "Investment"];

// Map wallet_type groups to the redesign's Debit/Lent/Borrowed buckets.
function groupOf(wt: string): "Debit" | "Lent" | "Borrowed" {
  if (wt === "Lent") return "Lent";
  if (wt === "Borrowed" || wt === "Debt") return "Borrowed";
  return "Debit";
}
const GROUP_COLOR: Record<string, string> = {
  Debit: "var(--purch-teal)",
  Lent: "var(--purch-gold)",
  Borrowed: "var(--purch-coral)",
};

export default function WalletsPage() {
  const [authed, setAuthed] = useState(false);
  const [rows, setRows] = useState<WalletRow[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [form, setForm] = useState<WalletCreate>({ name: "", wallet_type: "Cash", balance: "", note: "", color: "" });
  const [wantFavorite, setWantFavorite] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [cardForm, setCardForm] = useState<WalletCreate>({ name: "", wallet_type: "Cash", balance: "", note: "", color: "" });
  const [cardSaving, setCardSaving] = useState(false);
  const [error, setError] = useState("");
  const [favVersion, setFavVersion] = useState(0); // increments to force re-render on favorite toggle
  const { push: toastPush } = useToast();

  useEffect(() => {
    if (error) toastPush(error, "danger");
  }, [error, toastPush]);

  /** Toggle favorite and force re-render so the star updates instantly. */
  function handleToggleFav(id: number) {
    if (!loadFavorites().has(id)) {
      const favs = loadFavorites();
      if (favs.size >= MAX_FAVORITES) {
        setError(favoriteLimitMessage(rows));
        return;
      }
    }
    toggleFav(id);
    setFavVersion((v) => v + 1);
  }

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

  // Bidirectional scroll reveal
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) entry.target.classList.add("is-visible");
          else entry.target.classList.remove("is-visible");
        });
      },
      { threshold: 0.1 }
    );
    const timer = setTimeout(() => {
      document.querySelectorAll(".purch-reveal").forEach((el) => observer.observe(el));
    }, 100);
    return () => { observer.disconnect(); clearTimeout(timer); };
  }, [authed]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim()) {
      setError("Name is required.");
      return;
    }
    const bal = parseFloat(form.balance);
    if (form.balance.trim() !== "" && (isNaN(bal) || bal < 0)) {
      setError("Starting balance can't be negative — enter 0 or more.");
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
      setForm({ name: "", wallet_type: "Cash", balance: "", note: "", color: "" });
      setFormOpen(false);
      await load();
      // After creation, add to favorites if requested
      if (wantFavorite && editingId == null) {
        // Check limit before adding
        const favsAfterCreate = loadFavorites();
        if (favsAfterCreate.size < MAX_FAVORITES) {
          // Find the newly created wallet by name (most recent match)
          const fresh = await api.wallets.list(true);
          const wallets = fresh.wallets || [];
          const newest = wallets.filter((w: WalletRow) => w.name === form.name.trim()).pop();
          if (newest) {
            toggleFav(newest.id);
          }
        }
      }
      setWantFavorite(false);
    } catch (e: any) {
      setError(e.message || (editingId != null ? "Failed to update wallet." : "Failed to create wallet."));
    } finally {
      setLoading(false);
    }
  }

  async function saveCard(id: number) {
    if (!cardForm.name.trim()) {
      setError("Name is required.");
      return;
    }
    const bal = parseFloat(cardForm.balance);
    if (cardForm.balance.trim() !== "" && (isNaN(bal) || bal < 0)) {
      setError("Starting balance can't be negative — enter 0 or more.");
      return;
    }
    setCardSaving(true);
    try {
      await api.wallets.update(id, cardForm);
      setEditingId(null);
      await load();
    } catch (e: any) {
      setError(e.message || "Failed to update wallet.");
    } finally {
      setCardSaving(false);
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
    } catch (e: any) {
      // Wallet may belong to a stale session — reload to sync
      if (e.message?.includes("404")) {
        await load();
      } else {
        throw e;
      }
    } finally {
      setLoading(false);
    }
  }

  if (!authed) {
    return (
      <PageShell active="/wallets">
        <div className="mx-auto max-w-md">
          <div className="rounded-2xl p-8 text-center" style={{ background: "var(--purch-paper)", boxShadow: "var(--purch-shadow-sm)" }}>
            <h1 className="font-sans font-semibold text-[30px] m-0 mb-2">Wallets</h1>
            <p className="text-[14px] text-[color:var(--purch-muted-ink)] m-0">Sign in to manage your wallets.</p>
            <a href="/" className={`${primaryButton} mt-4`}>Sign in</a>
          </div>
        </div>
      </PageShell>
    );
  }

  if (loading && !rows.length) {
    return (
      <PageShell active="/wallets">
        <div className="flex flex-col items-center justify-center gap-4 py-24">
          <div
            className="h-10 w-10 rounded-full border-2 border-[color:var(--purch-line)] border-t-[color:var(--purch-accent)] animate-spin"
            role="status"
            aria-label="Loading"
          />
          <p className="font-sans text-[14px] text-[color:var(--purch-muted-ink)] animate-pulse">
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
    <PageShell active="/wallets">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-6">
        <div>
          <div className={eyebrow}>Money sources</div>
          <h1 className="font-sans font-semibold text-[30px] mt-0 mb-2 m-0" style={{ letterSpacing: "-0.02em" }}>
            Wallets
          </h1>
          <p className="text-[14px] text-[color:var(--purch-muted-ink)] max-w-[480px] leading-relaxed m-0">
            Name each place your money sits. Purch subtracts a purchase from
            whichever wallet you pick in chat.
          </p>
        </div>
        <div className="flex gap-2.5">
          <button onClick={load} disabled={loading} className={`${outlineButton} text-[13px] disabled:opacity-60`}>
            <RefreshCw size={14} /> Refresh
          </button>
          <button onClick={() => { setEditingId(null); setForm({ name: "", wallet_type: "Cash", balance: "", note: "", color: "" }); setWantFavorite(false); setFormOpen(true); }} className="purch-btn-primary inline-flex items-center justify-center gap-2 rounded-full px-5 py-2.5 text-[13px] font-medium">
            <Plus size={14} /> New wallet
          </button>
        </div>
      </div>

      {/* Create / Edit form — shown immediately below the header when
          "New wallet" or "Edit" is clicked, above the summary cards. */}
      {formOpen && (
        <form onSubmit={submit} className="rounded-2xl p-5 mb-4" style={{ background: "var(--purch-paper)", boxShadow: "var(--purch-shadow-sm)" }}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-sans font-semibold text-lg m-0">{editingId != null ? "Edit wallet" : "New wallet"}</h3>
            {editingId != null && (
              <button type="button" onClick={() => { setEditingId(null); setForm({ name: "", wallet_type: "Cash", balance: "", note: "", color: "" }); setFormOpen(false); }} className="text-xs text-[color:var(--purch-taupe)] hover:text-[color:var(--purch-accent)]">
                Cancel edit
              </button>
            )}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <label className="flex flex-col gap-1">
              <div className="flex items-center justify-between">
                <span className={eyebrow}>Name</span>
                <button
                  type="button"
                  onClick={() => {
                    if (!wantFavorite) {
                      const favs = loadFavorites();
                      if (favs.size >= MAX_FAVORITES) {
                        setError(favoriteLimitMessage(rows));
                        return;
                      }
                    }
                    setWantFavorite(!wantFavorite);
                    setFavVersion((v) => v + 1);
                  }}
                  className="p-0.5 rounded hover:bg-black/5 transition-colors"
                  title={wantFavorite ? "Remove from favorites" : "Add to favorites"}
                >
                  <Star
                    size={16}
                    style={{ color: wantFavorite ? "#F59E0B" : "var(--purch-taupe)" }}
                    fill={wantFavorite ? "#F59E0B" : "none"}
                  />
                </button>
              </div>
              <input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                maxLength={40}
                placeholder="e.g. GCash"
                className="rounded-lg px-3.5 py-2.5 text-sm bg-white"
                style={{ border: "1px solid var(--purch-line-soft)" }}
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className={eyebrow}>Type</span>
              <select
                value={form.wallet_type}
                onChange={(e) => setForm({ ...form, wallet_type: e.target.value })}
                className="rounded-lg px-3.5 py-2.5 text-sm bg-white"
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
                className="rounded-lg px-3.5 py-2.5 text-sm bg-white"
                style={{ border: "1px solid var(--purch-line-soft)" }}
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className={eyebrow}>Note</span>
              <input
                value={form.note}
                onChange={(e) => setForm({ ...form, note: e.target.value })}
                placeholder="optional"
                className="rounded-lg px-3.5 py-2.5 text-sm bg-white"
                style={{ border: "1px solid var(--purch-line-soft)" }}
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className={eyebrow}>Color</span>
              <div className="flex flex-wrap gap-2 items-center">
                {["#F4C542", "#7EB8E5", "#E88D9A", "#8FD5C5", "#C4A8E0", "#7ECFC4", "#D4A574", "#A8A8A8", "#8FD1A8", "#D6A0D6"].map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setForm({ ...form, color: form.color === c ? "" : c })}
                    className="w-7 h-7 rounded-full border-2 transition-all flex-shrink-0"
                    style={{
                      background: c,
                      borderColor: form.color === c ? "var(--purch-ink)" : "transparent",
                      boxShadow: form.color === c ? `0 0 0 2px var(--purch-bg), 0 0 0 4px ${c}` : "none",
                    }}
                    title={form.color === c ? "Remove color" : c}
                  />
                ))}
              </div>
            </label>
          </div>
          <div className="flex gap-2 mt-4">
            <button type="submit" disabled={loading} className={`${primaryButton} text-sm disabled:opacity-60`}>
              {loading ? "Saving…" : editingId != null ? "Save changes" : "Save wallet"}
            </button>
            <button type="button" onClick={() => { setFormOpen(false); setError(""); setWantFavorite(false); }} className={`${outlineButton} text-sm`}>
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Net worth / Assets / Liabilities */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5 mb-5">
        <div className="rounded-2xl p-5" style={{ background: "var(--purch-paper)", boxShadow: "var(--purch-shadow-sm)" }}>
          <div className={eyebrow}>Net worth</div>
          <div className="font-['JetBrains_Mono'] text-[28px] mt-2" style={{ color: "var(--purch-ink)" }}>
            ₱{summary?.net_display ?? "0.00"}
          </div>
          <div className="text-xs text-[color:var(--purch-muted-ink)] mt-1.5">Everything you hold, minus everything you owe.</div>
        </div>
        <div className="rounded-2xl p-5" style={{ background: "var(--purch-paper)", boxShadow: "var(--purch-shadow-sm)" }}>
          <div className={eyebrow}>Assets</div>
          <div className="font-['JetBrains_Mono'] text-[24px] mt-2" style={{ color: "var(--purch-ink)" }}>
            ₱{summary?.assets_display ?? "0.00"}
          </div>
          <div className="text-xs text-[color:var(--purch-muted-ink)] mt-1.5">Cash, bank, savings, and money you've lent out — what you own.</div>
        </div>
        <div className="rounded-2xl p-5" style={{ background: "var(--purch-paper)", boxShadow: "var(--purch-shadow-sm)" }}>
          <div className={eyebrow}>Liabilities</div>
          <div className="font-['JetBrains_Mono'] text-[24px] mt-2" style={{ color: "var(--purch-ink)" }}>
            ₱{summary?.liabilities_display ?? "0.00"}
          </div>
          <div className="text-xs text-[color:var(--purch-muted-ink)] mt-1.5">Debts and money you've borrowed — what you owe.</div>
        </div>
      </div>

      {/* Where your money sits */}
      <div className="rounded-2xl p-5 mb-4" style={{ background: "var(--purch-paper)", boxShadow: "var(--purch-shadow-sm)" }}>
        <div className="flex justify-between items-baseline mb-4">
          <h3 className="font-sans font-semibold text-lg m-0">Where your money sits</h3>
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
              <div key={g} className="rounded-xl p-4" style={{ background: "var(--purch-paper-soft)" }}>
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

      {/* Wallet cards — square, rounded */}
      {active.length === 0 && !loading ? (
        <div className="rounded-2xl p-10 text-center text-[color:var(--purch-muted-ink)]" style={{ background: "var(--purch-paper)", boxShadow: "var(--purch-shadow-sm)" }}>
          No wallets yet — create one to start tracking where your money lives.
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3.5">
          {active.map((w) => {
            const editing = editingId === w.id;
            if (editing) {
              return (
                <div
                  key={w.id}
                  className="rounded-2xl p-4 flex flex-col gap-3"
                  style={{ background: "var(--purch-paper)", boxShadow: "var(--purch-shadow-sm)" }}
                >
                  <div className="flex flex-col gap-2">
                    <label className="flex flex-col gap-1">
                      <span className={eyebrow}>Name</span>
                      <input value={cardForm.name} onChange={(e) => setCardForm({ ...cardForm, name: e.target.value })} className="rounded-lg px-2.5 py-1.5 text-sm" style={{ border: "1px solid var(--purch-line-soft)" }} />
                    </label>
                    <label className="flex flex-col gap-1">
                      <span className={eyebrow}>Type</span>
                      <select value={cardForm.wallet_type} onChange={(e) => setCardForm({ ...cardForm, wallet_type: e.target.value })} className="rounded-lg px-2.5 py-1.5 text-sm" style={{ border: "1px solid var(--purch-line-soft)" }}>
                        {WALLET_TYPES.map((t) => (<option key={t} value={t}>{t}</option>))}
                      </select>
                    </label>
                    <label className="flex flex-col gap-1">
                      <span className={eyebrow}>Balance</span>
                      <input value={cardForm.balance} onChange={(e) => setCardForm({ ...cardForm, balance: e.target.value })} className="rounded-lg px-2.5 py-1.5 text-sm" style={{ border: "1px solid var(--purch-line-soft)" }} />
                    </label>
                    <label className="flex flex-col gap-1">
                      <span className={eyebrow}>Note</span>
                      <input value={cardForm.note} onChange={(e) => setCardForm({ ...cardForm, note: e.target.value })} className="rounded-lg px-2.5 py-1.5 text-sm" style={{ border: "1px solid var(--purch-line-soft)" }} />
                    </label>
                    <label className="flex flex-col gap-1">
                      <span className={eyebrow}>Color</span>
                      <div className="flex flex-wrap gap-1.5 items-center">
                        {["#F4C542", "#7EB8E5", "#E88D9A", "#8FD5C5", "#C4A8E0", "#7ECFC4", "#D4A574", "#A8A8A8", "#8FD1A8", "#D6A0D6"].map((c) => (
                          <button
                            key={c}
                            type="button"
                            onClick={() => setCardForm({ ...cardForm, color: cardForm.color === c ? "" : c })}
                            className="w-6 h-6 rounded-full border-2 transition-all flex-shrink-0"
                            style={{
                              background: c,
                              borderColor: cardForm.color === c ? "var(--purch-ink)" : "transparent",
                              boxShadow: cardForm.color === c ? `0 0 0 1px var(--purch-bg), 0 0 0 3px ${c}` : "none",
                            }}
                            title={cardForm.color === c ? "Remove color" : c}
                          />
                        ))}
                      </div>
                    </label>
                  </div>
                  <div className="flex gap-2 mt-1">
                    <button onClick={() => saveCard(w.id)} disabled={cardSaving} className={`${primaryButton} text-[12px] flex-1 disabled:opacity-60`}>
                      {cardSaving ? "Saving…" : "Save"}
                    </button>
                    <button onClick={() => { setEditingId(null); setError(""); }} className={`${outlineButton} text-[12px]`}>Cancel</button>
                  </div>
                </div>
              );
            }
            return (
              <div
                key={w.id}
                className="rounded-2xl p-4 flex flex-col"
                style={{ background: w.color || "var(--purch-paper)", color: w.color ? "#fff" : "var(--purch-ink)", boxShadow: "var(--purch-shadow-sm)", minHeight: 132 }}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="font-semibold text-[14px] leading-tight mb-2 break-words">{w.name}</div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] px-1.5 py-0.5 rounded whitespace-nowrap" style={{ background: w.color ? "rgba(255,255,255,0.2)" : "var(--purch-paper-soft)", color: w.color ? "#fff" : "var(--purch-muted-ink)" }}>
                      {w.wallet_type}
                    </span>
                    <button
                      type="button"
                      onClick={() => handleToggleFav(w.id)}
                      className="p-0.5 rounded hover:bg-black/5 transition-colors"
                      title={loadFavorites().has(w.id) ? "Remove from favorites" : "Add to favorites"}
                    >
                      <Star
                        size={12}
                        style={{ color: loadFavorites().has(w.id) ? "#F59E0B" : "var(--purch-taupe)" }}
                        fill={loadFavorites().has(w.id) ? "#F59E0B" : "none"}
                      />
                    </button>
                  </div>
                </div>
                <div className="font-['JetBrains_Mono'] text-[20px] mt-auto">₱{w.balance_display}</div>
                {w.note ? <div className="text-[11px] mt-1 truncate" title={w.note} style={{ color: w.color ? "rgba(255,255,255,0.7)" : "var(--purch-muted-ink)" }}>{w.note}</div> : null}
                <div className="flex gap-3 text-[11.5px] mt-3 pt-2" style={{ borderTop: w.color ? "1px solid rgba(255,255,255,0.2)" : "1px solid var(--purch-line-soft)" }}>
                  <button
                    onClick={() => { setCardForm({ name: w.name, wallet_type: w.wallet_type, balance: String(w.balance), note: w.note ?? "", color: w.color ?? "" }); setEditingId(w.id); }}
                    className="hover:opacity-70 transition-opacity"
                    style={{ color: w.color ? "#fff" : "var(--purch-taupe)" }}
                  >
                    Edit
                  </button>
                  <button onClick={() => archive(w.id)} className="hover:opacity-70 transition-opacity" style={{ color: w.color ? "#fff" : "var(--purch-taupe)" }}>Archive</button>
                  <button onClick={() => remove(w.id)} className="hover:opacity-70 transition-opacity" style={{ color: w.color ? "#fff" : "var(--purch-taupe)" }}>Delete</button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Archived */}
      {archived.length > 0 && (
        <div className="mt-8">
          <div className={eyebrow}>Archived</div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3.5 mt-2">
            {archived.map((w) => (
              <div
                key={w.id}
                className="rounded-2xl p-4 flex flex-col opacity-70"
                style={{ background: "var(--purch-paper)", boxShadow: "var(--purch-shadow-sm)", minHeight: 132 }}
              >
                <div className="font-semibold text-[14px] mb-2 break-words" style={{ color: "var(--purch-ink)" }}>{w.name}</div>
                <div className="font-['JetBrains_Mono'] text-[20px] mt-auto" style={{ color: "var(--purch-ink)" }}>₱{w.balance_display}</div>
                <div className="flex gap-3 text-[11.5px] mt-3 pt-2" style={{ borderTop: "1px solid var(--purch-line-soft)" }}>
                  <button onClick={() => restore(w.id)} className="text-[color:var(--purch-taupe)] hover:text-[color:var(--purch-teal)] transition-colors">Restore</button>
                  <button onClick={() => remove(w.id)} className="text-[color:var(--purch-taupe)] hover:text-[color:var(--purch-accent)] transition-colors">Delete</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </PageShell>
  );
}
