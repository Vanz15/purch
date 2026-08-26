"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { api, ChatMessage, ChatResponse, WalletRow, BudgetStatusRow, AnalyticsResponse } from "@/lib/api";
import {
  PageShell,
  primaryButton,
  outlineButton,
  eyebrow,
} from "@/lib/ui";
import { PerforatedEdge, ReceiptHeader } from "@/lib/receipt";
import { ChatSidebar } from "@/components/ChatSidebar";
import { isGuest, ensureGuest, guestName, clearGuest } from "@/lib/guest";

const PROMPT_CHIPS = [
  "milk tea 85 cash",
  "grab ride 240 cash",
  "borrowed 250 from Aivann",
  "lent 300 to Curry",
  "how much this week?",
  "set food budget to 3000",
];

function ReceiptLine({ children }: { children: React.ReactNode }) {
  return <div className="purch-receipt-line">{children}</div>;
}

export default function ChatPage() {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [authed, setAuthed] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [pendingWallet, setPendingWallet] = useState<Record<string, any> | null>(null);
  const [walletChoices, setWalletChoices] = useState<any[]>([]);
  const [awaitingWallet, setAwaitingWallet] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  // Sidebar live data
  const [guestLabel, setGuestLabel] = useState("Guest");
  const [monthLabel, setMonthLabel] = useState("This month");
  const [spent, setSpent] = useState(0);
  const [budgetTotal, setBudgetTotal] = useState(0);
  const [budgets, setBudgets] = useState<BudgetStatusRow[]>([]);
  const [wallets, setWallets] = useState<WalletRow[]>([]);
  const [tone, setTone] = useState("neutral");

  const loadSidebar = useCallback(async () => {
    try {
      const [ana, w] = await Promise.all([
        api.analytics.get(0, 0),
        api.wallets.list(true),
      ]);
      const a: AnalyticsResponse = ana;
      setMonthLabel(a.month_label || "This month");
      setSpent(a.kpi.total ?? 0);
      setBudgets(a.budgets ?? []);
      setBudgetTotal(
        (a.budgets ?? []).reduce((s, b) => s + (b.limit_amount || 0), 0)
      );
      setWallets((w.wallets || []).filter((x: WalletRow) => !x.is_archived));
      try {
        const t = await api.tone.get();
        if (t?.tone) setTone(t.tone);
      } catch {
        /* tone optional */
      }
    } catch {
      /* sidebar stays at defaults */
    }
  }, []);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getSession().then(({ data }) => {
      if (data.session?.user) {
        const u = data.session.user;
        const name =
          (u.user_metadata?.full_name as string | undefined) ||
          (u.user_metadata?.name as string | undefined) ||
          u.email ||
          "Account";
        setGuestLabel(name);
        setAuthed(true);
      } else if (isGuest()) {
        ensureGuest();
        setGuestLabel(guestName());
        setAuthed(true);
      } else {
        setAuthed(false);
      }
      setReady(true);
    });
  }, []);

  useEffect(() => {
    if (authed) loadSidebar();
  }, [authed, loadSidebar]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  const send = useCallback(
    async (text?: string) => {
      const value = (text ?? draft).trim();
      if (!value || busy || awaitingWallet) return;
      setBusy(true);
      setError("");
      setDraft("");
      const userMsg: ChatMessage = {
        role: "user",
        text: value,
        meta: "",
        time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        alert: "",
      };
      setMessages((m) => [...m, userMsg]);
      try {
        const res: ChatResponse = await api.chat.send({
          message: value,
          pending_wallet: pendingWallet,
          wallet_choices: walletChoices,
          awaiting_wallet: awaitingWallet,
        });
        setMessages((m) => [
          ...m,
          {
            role: "assistant",
            text: res.response,
            meta: res.meta,
            time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            alert: res.alert as any,
          },
        ]);
        setPendingWallet(res.pending_wallet);
        setWalletChoices(res.wallet_choices);
        setAwaitingWallet(res.awaiting_wallet);
        loadSidebar(); // refresh budgets / wallets live
      } catch (e: any) {
        if (e.message === "AUTH_REQUIRED") {
          setError("Please sign in (Google or email) to save your data. Guest mode can't reach the backend yet.");
        } else {
          setError(e.message || "Request failed.");
        }
      } finally {
        setBusy(false);
      }
    },
    [draft, busy, awaitingWallet, pendingWallet, walletChoices, loadSidebar]
  );

  async function chooseWallet(id: number) {
    if (!pendingWallet) return;
    setBusy(true);
    try {
      const res: ChatResponse = await api.chat.chooseWallet({
        wallet_id: id,
        pending_wallet: pendingWallet,
      });
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          text: res.response,
          meta: "",
          time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          alert: res.alert as any,
        },
      ]);
      setPendingWallet(null);
      setWalletChoices([]);
      setAwaitingWallet(false);
      loadSidebar();
    } catch (e: any) {
      setError(e.message || "Wallet choice failed.");
    } finally {
      setBusy(false);
    }
  }

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

  if (!ready) {
    return (
      <main className="min-h-screen flex items-center justify-center text-[color:var(--purch-taupe)]">
        Loading…
      </main>
    );
  }

  if (!authed) {
    return (
      <PageShell active="/chat">
        <div className="mx-auto max-w-[640px]">
          <div
            className="rounded-lg p-8 text-center"
            style={{ background: "var(--purch-paper)", boxShadow: "var(--purch-shadow-sm)" }}
          >
            <h3 className="font-['Fraunces'] font-semibold text-2xl mt-0 mb-3 m-0">
              Sign in to start chatting.
            </h3>
            <p className="text-[color:var(--purch-taupe)] text-[15px] leading-relaxed mb-6 max-w-md mx-auto">
              Purch keeps every purchase, budget, and tone tied to your account.
              Sign in with Google or email — or continue as a guest to preview
              the experience privately on this device.
            </p>
            <div className="flex flex-wrap items-center justify-center gap-3">
              <a href="/login" className={primaryButton}>
                Sign in
              </a>
              <button
                onClick={() => {
                  ensureGuest();
                  setGuestLabel(guestName());
                  setAuthed(true);
                }}
                className={outlineButton}
              >
                Continue as guest
              </button>
            </div>
          </div>
        </div>
      </PageShell>
    );
  }

  const hasStarted = messages.length > 0;

  const sidebarNode = (
    <ChatSidebar
      monthLabel={monthLabel}
      spent={spent}
      budgetTotal={budgetTotal}
      budgets={budgets}
      wallets={wallets}
      tone={tone}
      onToneChange={changeTone}
      guestLabel={guestLabel}
      onSignOut={signOut}
    />
  );

  return (
    <PageShell active="/chat" sidebar={sidebarNode}>
      <div className="mx-auto max-w-[680px]">
        {error && (
          <div className="flex items-center gap-3 mb-4 p-3 rounded-lg border" style={{ borderColor: "var(--purch-rust)", background: "var(--purch-paper)" }}>
            <span className="font-bold" style={{ color: "var(--purch-rust)" }}>⚠</span>
            <p className="text-sm flex-1 m-0">{error}</p>
          </div>
        )}

        {/* The whole chat lives inside one receipt: header -> body (greeting OR thread) -> composer -> perforated edge */}
        <div
          className="rounded-md overflow-hidden"
          style={{ background: "var(--purch-paper)", boxShadow: "var(--purch-shadow-sm)" }}
        >
          <ReceiptHeader title="Live receipt" tone={tone} />

          <div className="px-5 py-4">
            {!hasStarted ? (
              /* Empty state: greeting + description + example chips, all inside the receipt */
              <div className="text-center py-6">
                <div
                  className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl font-['Fraunces'] font-bold text-lg"
                  style={{ background: "var(--purch-ink)", color: "var(--purch-gold)" }}
                >
                  P
                </div>
                <h2 className="font-['Fraunces'] font-semibold text-[26px] mt-0 mb-2 m-0">
                  Hey! I&apos;m Purch.
                </h2>
                <p className="text-[14px] text-[color:var(--purch-taupe)] leading-relaxed max-w-[440px] mx-auto mb-6">
                  Tell me what you bought and which wallet it came from, log what
                  you borrowed or lent, ask what you spent, or set a budget. No
                  forms, no dropdowns — just a quick, natural chat.
                </p>
                <div className="flex flex-wrap gap-2 justify-center">
                  {PROMPT_CHIPS.map((c) => (
                    <button
                      key={c}
                      onClick={() => send(c)}
                      className="text-[12.5px] px-3.5 py-1.5 rounded-[20px] cursor-pointer"
                      style={{ border: "1px solid var(--purch-line-soft)", background: "var(--purch-paper)", color: "var(--purch-ink)" }}
                    >
                      {c}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              /* Thread */
              <div className="max-h-[52vh] overflow-y-auto">
                {messages.map((m, i) =>
                  m.role === "user" ? (
                    <div key={i} className="flex justify-end py-2.5">
                      <div className="purch-bubble-user max-w-[78%]">{m.text}</div>
                    </div>
                  ) : (
                    <ReceiptLine key={i}>
                      {m.alert === "warning" && (
                        <span className="font-bold uppercase text-[0.65rem] tracking-[0.1em] mr-1" style={{ color: "var(--purch-gold)" }}>
                          ⚠ Budget warning —{" "}
                        </span>
                      )}
                      {m.alert === "danger" && (
                        <span className="font-bold uppercase text-[0.65rem] tracking-[0.1em] mr-1" style={{ color: "var(--purch-rust)" }}>
                          ⚠ Over budget —{" "}
                        </span>
                      )}
                      {m.text}
                      {m.meta && (
                        <div className="mt-1 text-[12.5px]" style={{ color: "var(--purch-pine)" }}>
                          {m.meta}
                        </div>
                      )}
                    </ReceiptLine>
                  )
                )}
                {busy && (
                  <ReceiptLine>
                    <span className="opacity-60">Purch is writing…</span>
                  </ReceiptLine>
                )}
                <div ref={endRef} />
              </div>
            )}
          </div>

          {/* Composer — always inside the receipt */}
          {awaitingWallet ? (
            <div className="px-5 pb-4">
              <div className="text-[11px] uppercase tracking-[0.1em] text-[color:var(--purch-taupe)] mb-2">
                Pick a wallet — required
              </div>
              <div className="flex flex-wrap gap-2">
                {walletChoices.map((w) => (
                  <button
                    key={w.id}
                    onClick={() => chooseWallet(w.id)}
                    className="flex flex-col items-start gap-0.5 px-3.5 py-2 rounded-lg text-left"
                    style={{ background: "var(--purch-paper)", border: "1px solid var(--purch-line-soft)" }}
                  >
                    <span className="text-sm font-semibold">{w.name}</span>
                    <span className="font-['JetBrains_Mono'] text-[0.65rem] text-[color:var(--purch-taupe)]">
                      {w.wallet_type} · ₱{w.balance_display}
                    </span>
                  </button>
                ))}
              </div>
              <p className="text-xs text-[color:var(--purch-taupe)] mt-3 m-0">
                Every purchase needs a wallet so your balances stay accurate.
              </p>
            </div>
          ) : (
            <div className="px-5 pb-4 flex gap-2.5">
              <input
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                disabled={busy}
                onKeyDown={(e) => e.key === "Enter" && send()}
                placeholder='Try "milk tea ₱85" or "how much this week?"'
                className="flex-1 px-4 py-3.5 rounded-lg text-[14px] bg-[color:var(--purch-paper)] disabled:opacity-60"
                style={{ border: "1px solid var(--purch-line-soft)" }}
              />
              <button
                onClick={() => send()}
                disabled={busy}
                className={`${primaryButton} px-6 disabled:opacity-60`}
              >
                Send
              </button>
            </div>
          )}

          <PerforatedEdge />
        </div>
      </div>
    </PageShell>
  );
}
