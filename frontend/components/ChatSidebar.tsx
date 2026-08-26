"use client";

import { LogOut } from "lucide-react";

const TONE_OPTIONS = ["neutral", "bestie", "sarcastic"];

export interface ChatSidebarProps {
  monthLabel: string;
  spent: number;
  budgetTotal: number;
  budgets: {
    category: string;
    limit_amount: number;
    spent: number;
    pct: number;
    remaining: number;
    status: "on_track" | "near" | "over";
  }[];
  wallets: { name: string; balance: number; wallet_type: string }[];
  tone: string;
  onToneChange: (t: string) => void;
  guestLabel: string;
  onSignOut: () => void;
}

export function ChatSidebar(props: ChatSidebarProps) {
  const {
    monthLabel,
    spent,
    budgetTotal,
    budgets,
    wallets,
    tone,
    onToneChange,
    guestLabel,
    onSignOut,
  } = props;

  const spentPct = budgetTotal > 0 ? Math.min((spent / budgetTotal) * 100, 100) : 0;
  const maxWallet = Math.max(1, ...wallets.map((w) => Math.abs(w.balance)));

  return (
    <aside
      className="hidden sm:flex w-[280px] shrink-0 flex-col text-[color:var(--purch-paper)] overflow-y-auto"
      style={{ background: "var(--purch-ink)" }}
    >
      {/* Receipt-style total card */}
      <div
        className="purch-receipt-header"
        style={{ background: "transparent", borderBottom: "1px dashed rgba(248,243,231,0.25)" }}
      >
        <span className="title" style={{ color: "var(--purch-gold)" }}>
          {monthLabel.toUpperCase()} — TOTAL
        </span>
      </div>
      <div className="px-5 py-4">
        <div className="flex items-center justify-between mb-2 text-[12px]">
          <span className="font-['JetBrains_Mono']">{spentPct.toFixed(0)}%</span>
          <span className="font-['JetBrains_Mono']">
            ₱{spent.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </span>
        </div>
        <div className="h-2 rounded-full" style={{ background: "#3A2E26" }}>
          <div
            className="h-full rounded-full"
            style={{
              width: `${spentPct}%`,
              background: spentPct >= 100 ? "var(--purch-rust)" : "var(--purch-gold)",
            }}
          />
        </div>
      </div>

      {/* Budgets */}
      <div className="px-5 pb-5">
        <div className="text-[10px] uppercase tracking-[0.12em] text-[color:var(--purch-taupe)] mb-2">
          Budgets
        </div>
        {budgets.length === 0 ? (
          <p className="text-[12.5px] leading-relaxed text-[#B8AC9C] italic">
            No budgets set yet — try &quot;set food budget to 3000&quot; in chat.
          </p>
        ) : (
          <div className="flex flex-col gap-3">
            {budgets.map((b, i) => (
              <div key={i}>
                <div className="flex justify-between text-[12.5px] mb-1">
                  <span className="font-semibold">{b.category}</span>
                  <span className="font-['JetBrains_Mono] text-[color:var(--purch-gold)]">
                    ₱{b.spent.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    <span className="text-[color:var(--purch-taupe)]">
                      /{b.limit_amount.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </span>
                  </span>
                </div>
                <div className="h-1.5 rounded-full" style={{ background: "#3A2E26" }}>
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
      <div className="px-5 pb-5">
        <div className="text-[10px] uppercase tracking-[0.12em] text-[color:var(--purch-taupe)] mb-2">
          Spendable wallets
        </div>
        {wallets.length === 0 ? (
          <p className="text-[12.5px] leading-relaxed text-[#B8AC9C] italic">
            No spendable wallets yet — add a Cash or Bank wallet to track what you can spend.
          </p>
        ) : (
          <div className="flex flex-col gap-3">
            {wallets.map((w, i) => {
              const barPct = Math.min((Math.abs(w.balance) / maxWallet) * 100, 100);
              return (
                <div key={i}>
                  <div className="flex justify-between items-baseline mb-1">
                    <span className="text-[12.5px] font-semibold">{w.name}</span>
                    <span className="font-['JetBrains_Mono'] text-[12.5px] text-[color:var(--purch-pine)]">
                      ₱{w.balance.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                    </span>
                  </div>
                  <div className="h-1.5 rounded-full" style={{ background: "#3A2E26" }}>
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
      <div className="px-5 pb-5">
        <div className="text-[10px] uppercase tracking-[0.12em] text-[color:var(--purch-taupe)] mb-2">
          Tone
        </div>
        <select
          value={tone}
          onChange={(e) => onToneChange(e.target.value)}
          className="w-full rounded-md px-3 py-2 text-[13px]"
          style={{
            background: "#2A201A",
            color: "var(--purch-paper)",
            border: "1px solid #3A2E26",
          }}
        >
          {TONE_OPTIONS.map((t) => (
            <option key={t} value={t} style={{ background: "#2A201A" }}>
              {t}
            </option>
          ))}
        </select>
      </div>

      {/* Profile + sign out */}
      <div className="mt-auto px-5 py-4 border-t flex items-center justify-between" style={{ borderColor: "rgba(248,243,231,0.15)" }}>
        <div className="flex items-center gap-2.5">
          <div
            className="flex h-8 w-8 items-center justify-center rounded-full font-['Fraunces'] font-bold text-[13px]"
            style={{ background: "var(--purch-gold)", color: "var(--purch-ink)" }}
          >
            P
          </div>
          <div className="leading-tight">
            <div className="text-[13px] font-semibold">{guestLabel}</div>
            <div className="text-[10px] uppercase tracking-[0.08em] text-[color:var(--purch-taupe)]">
              Guest session
            </div>
          </div>
        </div>
        <button
          onClick={onSignOut}
          className="flex items-center gap-1 text-[12px] font-semibold"
          style={{ color: "var(--purch-rust)" }}
        >
          <LogOut size={14} /> Sign out
        </button>
      </div>
    </aside>
  );
}
