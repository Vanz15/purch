"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { api, ChatMessage, ChatResponse, WalletRow } from "@/lib/api";
import {
  PageShell,
  primaryButton,
  outlineButton,
  eyebrow,
  useToast,
} from "@/lib/ui";
import { PerforatedEdge, ReceiptHeader } from "@/lib/receipt";
import { ChatSidebar } from "@/components/ChatSidebar";
import { isGuest, ensureGuest } from "@/lib/guest";

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

// Persist the chat across page navigation (SPA route changes unmount/remount
// the page, which would otherwise wipe the thread). sessionStorage is per-tab,
// so a fresh tab starts clean — which is the behaviour we want.
const CHAT_KEY = "purch:chat:v1";
type ChatPersist = {
  messages: ChatMessage[];
  pendingWallet: Record<string, any> | null;
  walletChoices: any[];
  awaitingWallet: boolean;
};
function saveChat(s: ChatPersist) {
  try {
    sessionStorage.setItem(CHAT_KEY, JSON.stringify(s));
  } catch {
    /* ignore quota / serialization errors */
  }
}
function loadChat(): ChatPersist | null {
  try {
    const raw = sessionStorage.getItem(CHAT_KEY);
    return raw ? (JSON.parse(raw) as ChatPersist) : null;
  } catch {
    return null;
  }
}
function groupOf(wt: string): "Debit" | "Lent" | "Borrowed" {
  if (wt === "Lent") return "Lent";
  if (wt === "Borrowed" || wt === "Debt") return "Borrowed";
  return "Debit";
}

export default function ChatPage() {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [authed, setAuthed] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>(() => loadChat()?.messages ?? []);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const toast = useToast();
  const [pendingWallet, setPendingWallet] = useState<Record<string, any> | null>(
    () => loadChat()?.pendingWallet ?? null
  );
  const [walletChoices, setWalletChoices] = useState<any[]>(
    () => loadChat()?.walletChoices ?? []
  );
  const [awaitingWallet, setAwaitingWallet] = useState<boolean>(
    () => loadChat()?.awaitingWallet ?? false
  );
  // Debit wallets available — fetched so we only force "pick a wallet" when at
  // least one Debit wallet exists. With none, the chat defaults to cash.
  const [hasDebitWallets, setHasDebitWallets] = useState(false);
  const [walletCheckLoading, setWalletCheckLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getSession().then(({ data }) => {
      if (data.session?.user) {
        setAuthed(true);
      } else if (isGuest()) {
        ensureGuest();
        setAuthed(true);
      } else {
        setAuthed(false);
      }
      setReady(true);
    });
  }, []);

  // Check whether any Debit wallets exist (drives the "pick a wallet" gate).
  useEffect(() => {
    if (!authed) return;
    let cancelled = false;
    setWalletCheckLoading(true);
    api.wallets
      .list(true)
      .then((w) => {
        if (cancelled) return;
        const has = (w.wallets || []).some(
          (x: WalletRow) => !x.is_archived && groupOf(x.wallet_type) === "Debit"
        );
        setHasDebitWallets(has);
      })
      .catch(() => {})
      .finally(() => !cancelled && setWalletCheckLoading(false));
    return () => {
      cancelled = true;
    };
  }, [authed]);

  // Persist the thread on every change so navigating away and back keeps it.
  useEffect(() => {
    if (!ready) return;
    saveChat({ messages, pendingWallet, walletChoices, awaitingWallet });
  }, [messages, pendingWallet, walletChoices, awaitingWallet, ready]);

  // Surfaced notifications: error + assistant budget warnings appear as a
  // global toast (top-center, visible at any scroll position) so the user
  // is notified immediately even when scrolled to the bottom on mobile.
  useEffect(() => {
    if (error) toast.push(error, "danger");
  }, [error, toast]);

  useEffect(() => {
    const last = messages[messages.length - 1];
    if (last && last.role === "assistant" && last.alert) {
      toast.push(last.text, last.alert === "danger" ? "danger" : "warning");
    }
    // Only react to the newest assistant message's alert.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages.length]);

  function clearChat() {
    setMessages([]);
    setDraft("");
    setPendingWallet(null);
    setWalletChoices([]);
    setAwaitingWallet(false);
    setError("");
    try {
      sessionStorage.removeItem(CHAT_KEY);
    } catch {
      /* ignore */
    }
  }

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
          require_wallet: hasDebitWallets,
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
        window.dispatchEvent(new Event("purch:refresh-sidebar")); // refresh sidebar live
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
    [draft, busy, awaitingWallet, pendingWallet, walletChoices]
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
      window.dispatchEvent(new Event("purch:refresh-sidebar"));
    } catch (e: any) {
      setError(e.message || "Wallet choice failed.");
    } finally {
      setBusy(false);
    }
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
              Sign in with Google or continue as a guest to preview
              the experience privately on this device.
            </p>
            <div className="flex flex-wrap items-center justify-center gap-3">
              <a href="/" className={primaryButton}>
                Sign in
              </a>
              <button
                onClick={() => {
                  ensureGuest();
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

  return (
    <PageShell active="/chat" sidebar={<ChatSidebar />}>
      <div className="mx-auto max-w-[680px]">
        {error && (
          <div className="flex items-center gap-3 mb-4 p-3 rounded-lg border" style={{ borderColor: "var(--purch-rust)", background: "var(--purch-paper)" }}>
            <span className="font-bold" style={{ color: "var(--purch-rust)" }}>⚠</span>
            <p className="text-sm flex-1 m-0">{error}</p>
          </div>
        )}

        <div className="flex justify-end mb-3">
          <button
            onClick={clearChat}
            disabled={!hasStarted}
            className={`${outlineButton} text-[12.5px] disabled:opacity-40`}
          >
            Clear chat
          </button>
        </div>

        {/* The whole chat lives inside one receipt: header -> body (greeting OR thread) -> composer -> perforated edge */}
        <div
          className="rounded-md overflow-hidden"
          style={{ background: "var(--purch-paper)", boxShadow: "var(--purch-shadow-sm)" }}
        >
          <ReceiptHeader title="Live receipt" />

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
                      onClick={() => {
                        setDraft(c);
                        inputRef.current?.focus();
                      }}
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
                    <div key={i} className="flex items-start gap-2.5 py-2.5">
                      <div
                        className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full font-['Fraunces'] font-bold text-[13px]"
                        style={{ background: "var(--purch-ink)", color: "var(--purch-gold)" }}
                      >
                        P
                      </div>
                      <div className="flex-1">
                        <ReceiptLine>
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
                      </div>
                    </div>
                  )
                )}
                {busy && (
                  <div className="flex items-start gap-2.5 py-2.5">
                    <div
                      className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full font-['Fraunces'] font-bold text-[13px]"
                      style={{ background: "var(--purch-ink)", color: "var(--purch-gold)" }}
                    >
                      P
                    </div>
                    <div className="flex-1">
                      <ReceiptLine>
                        <span className="opacity-60">Purch is writing…</span>
                      </ReceiptLine>
                    </div>
                  </div>
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
                ref={inputRef}
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
