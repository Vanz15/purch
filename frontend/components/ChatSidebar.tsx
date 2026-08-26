"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { LogOut, RefreshCw } from "lucide-react";
import { api, WalletRow, BudgetStatusRow, AnalyticsResponse } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";
import { isGuest, guestName, clearGuest } from "@/lib/guest";

const TONE_OPTIONS = ["neutral", "bestie", "sarcastic"];

export function ChatSidebar() {
  const router = useRouter();
  const [monthLabel, setMonthLabel] = useState("This month");
  const [spent, setSpent] = useState(0);
  const [budgetTotal, setBudgetTotal] = useState(0);
  const [budgets, setBudgets] = useState<BudgetStatusRow[]>([]);
  const [wallets, setWallets] = useState<WalletRow[]>([]);
  const [tone, setTone] = useState("neutral");
  const [guestLabel, setGuestLabel] = useState("Guest");
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const [ana, w] = await Promise.all([api.analytics.get(0, 0), api.wallets.list(true)]);
      const a: AnalyticsResponse = ana;
      setMonthLabel(a.month_label || "This month");
      setSpent(a.kpi.total ?? 0);
      setBudgets(a.budgets ?? []);
      setBudgetTotal((a.budgets ?? []).reduce((s, b) => s + (b.limit_amount || 0), 0));
      setWallets((w.wallets || []).filter((x: WalletRow) => !x.is_archived));
      try {
        const t = await api.tone.get();
        if (t?.tone) setTone(t.tone);
      } catch {
        /* tone optional */
      }
    } catch {
      /* keep defaults */
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getSession().then(({ data }) => {
      if (data.session?.user) {
        const u = data.session.user;
        setGuestLabel(
          (u.user_metadata?.full_name as string | undefined) ||
            (u.user_metadata?.name as string | undefined) ||
            u.email ||
            "Account"
        );
      } else if (isGuest()) {
        setGuestLabel(guestName());
      }
    });
    load();
    const onRefresh = () => load();
    window.addEventListener("purch:refresh-sidebar", onRefresh);
    return () => window.removeEventListener("purch:refresh-sidebar", onRefresh);
  }, []);

  async function changeTone(t: string) {
    setTone(t);
    try {
      await api.tone.set(t);
    } catch {
      /* ignore */
    }
  }

  function signOut() {
    const supabase = createClient();
    supabase.auth.signOut().finally(() => {
      clearGuest();
      router.push("/login");
    });
  }

  const spentPct = budgetTotal > 0 ? Math.min((spent / budgetTotal) * 100, 100) : 0;
  const maxWallet = Math.max(1, ...wallets.map((w) => Math.abs(w.balance)));

  return (
    <aside className="w-full lg:w-[280px] lg:shrink-0 flex flex-col gap-3 bg-[color:var(--purch-bg)] overflow-y-auto p-3 pt-5 lg:p-0 lg:pt-6 lg:px-0 lg:bg-transparent lg:h-screen lg:sticky lg:top-0">
      {/* LIVE WALLET — the dark-brown receipt widget, large */}
      <div
        className="rounded-xl overflow-hidden shadow-[0_10px_30px_rgba(28,20,16,0.28)]"
        style={{ background: "var(--purch-ink)" }}
      >
        <div
          className="flex items-center justify-between px-4 pt-2.5"
          style={{ color: "var(--purch-gold)" }}
        >
          <span className="font-['JetBrains_Mono'] text-[10px] uppercase tracking-[0.12em]">
            {monthLabel.toUpperCase()} — TOTAL
          </span>
          <button
            onClick={load}
            aria-label="Refresh summary"
            className="opacity-70 hover:opacity-100 transition-opacity"
            style={{ color: "var(--purch-gold)" }}
          >
            <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
        <div className="px-4 pb-3 pt-1.5">
          <div className="font-['JetBrains_Mono'] font-bold leading-none" style={{ color: "var(--purch-paper)" }}>
            <span className="text-[18px] align-top mr-1" style={{ color: "var(--purch-gold)" }}>
              ₱
            </span>
            <span className="text-[32px]">
              {spent.toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </span>
          </div>
          <div className="flex items-center justify-between mt-2.5 text-[10px]" style={{ color: "#B8AC9C" }}>
            <span className="font-['JetBrains_Mono]">{spentPct.toFixed(0)}%</span>
            <span className="font-['JetBrains_Mono]">
              of ₱{budgetTotal.toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </span>
          </div>
          <div className="h-2.5 rounded-full mt-2" style={{ background: "#3A2E26" }}>
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${spentPct}%`,
                background: spentPct >= 100 ? "var(--purch-rust)" : "var(--purch-gold)",
              }}
            />
          </div>
        </div>
      </div>

      {/* Budgets */}
      <div className="rounded-xl border p-2.5" style={{ background: "var(--purch-paper)", borderColor: "var(--purch-line)" }}>
        <div className="text-[10px] uppercase tracking-[0.12em] text-[color:var(--purch-taupe)] mb-1.5">
          Budgets
        </div>
        {budgets.length === 0 ? (
          <p className="text-[12px] leading-relaxed text-[color:var(--purch-taupe)] italic">
            No budgets set yet — try &quot;set food budget to 3000&quot; in chat.
          </p>
        ) : (
          <div className="flex flex-col gap-3">
            {budgets.map((b, i) => (
              <div key={i}>
                <div className="flex justify-between text-[12px] mb-1">
                  <span className="font-semibold">{b.category}</span>
                  <span className="font-['JetBrains_Mono] text-[color:var(--purch-rust)]">
                    ₱{b.spent.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    <span className="text-[color:var(--purch-taupe)]">
                      /{b.limit_amount.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </span>
                  </span>
                </div>
                <div className="h-1.5 rounded-full" style={{ background: "var(--purch-line)" }}>
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${Math.min(b.pct, 100)}%`,
                      background:
                        b.status === "over"
                          ? "var(--purch-rust)"
                          : b.status === "near"
                          ? "var(--purch-gold)"
                          : "var(--purch-pine)",
                    }}
                  />
                </div>
                <div className="text-[10.5px] text-[color:var(--purch-taupe)] mt-1">
                  {b.remaining >= 0
                    ? `₱${b.remaining.toLocaleString(undefined, { maximumFractionDigits: 0 })} left`
                    : `₱${(-b.remaining).toLocaleString(undefined, { maximumFractionDigits: 0 })} over`}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Spendable wallets */}
      <div className="rounded-xl border p-2.5" style={{ background: "var(--purch-paper)", borderColor: "var(--purch-line)" }}>
        <div className="text-[10px] uppercase tracking-[0.12em] text-[color:var(--purch-taupe)] mb-1.5">
          Spendable wallets
        </div>
        {wallets.length === 0 ? (
          <p className="text-[12px] leading-relaxed text-[color:var(--purch-taupe)] italic">
            No spendable wallets yet — add a Cash or Bank wallet to track what you can spend.
          </p>
        ) : (
          <div className="flex flex-col gap-3">
            {wallets.map((w, i) => {
              const barPct = Math.min((Math.abs(w.balance) / maxWallet) * 100, 100);
              return (
                <div key={i}>
                  <div className="flex justify-between items-baseline mb-1">
                    <span className="text-[12px] font-semibold">{w.name}</span>
                    <span className="font-['JetBrains_Mono'] text-[12.5px]" style={{ color: "var(--purch-pine)" }}>
                      ₱{w.balance.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                    </span>
                  </div>
                  <div className="h-1.5 rounded-full" style={{ background: "var(--purch-line)" }}>
                    <div
                      className="h-full rounded-full"
                      style={{ width: `${barPct}%`, background: "var(--purch-pine)" }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Tone */}
      <div className="rounded-xl border p-2.5" style={{ background: "var(--purch-paper)", borderColor: "var(--purch-line)" }}>
        <div className="text-[10px] uppercase tracking-[0.12em] text-[color:var(--purch-taupe)] mb-1.5">
          Tone
        </div>
        <select
          value={tone}
          onChange={(e) => changeTone(e.target.value)}
          className="w-full rounded-md px-3 py-1.5 text-[12.5px]"
          style={{ background: "var(--purch-bg)", color: "var(--purch-ink)", border: "1px solid var(--purch-line-soft)" }}
        >
          {TONE_OPTIONS.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>

      {/* Profile + sign out */}
      <div className="rounded-xl border p-3 flex items-center justify-between" style={{ background: "var(--purch-paper)", borderColor: "var(--purch-line)" }}>
        <div className="flex items-center gap-2.5">
          <div
            className="flex h-7 w-7 items-center justify-center rounded-full font-['Fraunces'] font-bold text-[12px]"
            style={{ background: "var(--purch-gold)", color: "var(--purch-ink)" }}
          >
            P
          </div>
          <div className="leading-tight">
            <div className="text-[13px] font-semibold truncate max-w-[140px]">{guestLabel}</div>
            <div className="text-[10px] uppercase tracking-[0.08em] text-[color:var(--purch-taupe)]">
              Guest session
            </div>
          </div>
        </div>
        <button
          onClick={signOut}
          className="flex items-center gap-1 text-[12px] font-semibold"
          style={{ color: "var(--purch-rust)" }}
        >
          <LogOut size={14} /> Sign out
        </button>
      </div>
    </aside>
  );
}
