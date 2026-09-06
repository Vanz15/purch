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
import { AlertTriangle, Send, Trash2 } from "lucide-react";
import { isGuest, ensureGuest } from "@/lib/guest";
import { BudgetStatusCard } from "@/components/BudgetStatusCard";
import { MonthlySpendingCard } from "@/components/MonthlySpendingCard";
import { WalletStack } from "@/components/WalletStrip";
import { TransactionHistoryCard } from "@/components/TransactionHistoryCard";

const PROMPT_CHIPS = [
  "milk tea 85 Gcash",
  "set food budget to 3000",
  "how much did I spend this week?",
  "add 500 to my savings",
  "what's my total balance?",
];

const TONE_OPTIONS = ["neutral", "bestie", "sarcastic"] as const;

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
  const { push: toastPush } = useToast();
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
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Typewriter for greeting
  const [greetingText, setGreetingText] = useState("");


  // Tone — loaded from backend, persisted per-user
  const [tone, setTone] = useState<string>("neutral");
  const [userName, setUserName] = useState("");
  const [greetingDone, setGreetingDone] = useState(false);
  const greetingFull = `Hey, ${userName || "there"}! I'm Purch.`;

  useEffect(() => {
    const supabase = createClient();
    // Listen for auth state changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        if (session?.user) {
          setAuthed(true);
          const name = (session.user.user_metadata?.full_name as string) || (session.user.user_metadata?.name as string) || session.user.email || "";
          setUserName(name.split(" ")[0] || "there");
        } else if (isGuest()) {
          ensureGuest();
          setAuthed(true);
          const raw = localStorage.getItem("purch_guest_id") || "";
          const short = raw.replace("guest-", "").slice(0, 4);
          setUserName(`Guest${short}`);
        } else {
          setAuthed(false);
        }
        setReady(true);
      }
    );

    // Also check immediately
    supabase.auth.getSession().then(({ data }) => {
      if (data.session?.user) {
        setAuthed(true);
        const name = (data.session.user.user_metadata?.full_name as string) || (data.session.user.user_metadata?.name as string) || data.session.user.email || "";
        setUserName(name.split(" ")[0] || "there");
      } else if (isGuest()) {
        ensureGuest();
        setAuthed(true);
        const raw = localStorage.getItem("purch_guest_id") || "";
        const short = raw.replace("guest-", "").slice(0, 4);
        setUserName(`Guest${short}`);
      } else {
        setAuthed(false);
      }
      setReady(true);
    });

    return () => subscription.unsubscribe();
  }, []);

  // Load tone from backend
  useEffect(() => {
    if (!authed) return;
    api.tone.get().then((t) => {
      if (t?.tone) setTone(t.tone);
    }).catch(() => {});
  }, [authed]);

  // Bidirectional scroll reveal for dashboard cards
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
          } else {
            entry.target.classList.remove("is-visible");
          }
        });
      },
      { threshold: 0.1 }
    );
    const timer = setTimeout(() => {
      document.querySelectorAll(".purch-reveal").forEach((el) => observer.observe(el));
    }, 200);
    return () => { observer.disconnect(); clearTimeout(timer); };
  }, [authed]);

  async function changeTone(t: string) {
    setTone(t);
    try {
      await api.tone.set(t);
    } catch {
      /* ignore */
    }
  }

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
  // global toast (top-right, slides in from the right) so the user is
  // notified immediately even when scrolled to the bottom on mobile.
  // Depends only on [error] — toastPush is stable, so this won't loop.
  useEffect(() => {
    if (error) toastPush(error, "danger");
  }, [error, toastPush]);

  useEffect(() => {
    const last = messages[messages.length - 1];
    if (last && last.role === "assistant" && last.alert) {
      toastPush(last.text, last.alert === "danger" ? "danger" : "warning");
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
        const res = await api.chat.send({
          message: value,
          pending_wallet: pendingWallet,
          wallet_choices: walletChoices,
          awaiting_wallet: awaitingWallet,
          require_wallet: hasDebitWallets,
        }) as ChatResponse;
        setMessages((m) => [
          ...m,
          {
            role: "assistant",
            text: res.response || "",
            meta: res.meta,
            time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            alert: res.alert as any,
          },
        ]);
        setPendingWallet(res.pending_wallet);
        setWalletChoices(res.wallet_choices || []);
        setAwaitingWallet(res.awaiting_wallet || false);
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
      const res = await api.chat.chooseWallet({
        wallet_id: id,
        pending_wallet: pendingWallet,
      }) as ChatResponse;
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          text: res.response || "",
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

  const hasStarted = messages.length > 0;

  // Typewriter for greeting
  useEffect(() => {
    if (hasStarted) return;
    let idx = 0;
    const timer = setInterval(() => {
      idx++;
      setGreetingText(greetingFull.slice(0, idx));
      if (idx >= greetingFull.length) {
        clearInterval(timer);
        setGreetingDone(true);
      }
    }, 30);
    return () => clearInterval(timer);
  }, [hasStarted, greetingFull]);

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
            <h3 className="font-sans font-semibold text-2xl mt-0 mb-3 m-0">
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

  return (
    <PageShell active="/chat" >
      <div className="mx-auto max-w-[1400px]">
        <div className="grid grid-cols-1 xl:grid-cols-[1fr_380px] gap-5">
          {/* LEFT COLUMN — dashboard cards, scrollable on desktop */}
          <div className="flex flex-col gap-5">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5" style={{ gridAutoRows: "1fr" }}>
              <div className="purch-reveal"><BudgetStatusCard /></div>
              <div className="purch-reveal delay-100"><MonthlySpendingCard /></div>
            </div>
            <div className="purch-reveal delay-200"><TransactionHistoryCard /></div>
          </div>

          {/* RIGHT COLUMN — wallet stack + chat receipt */}
      <div className="flex flex-col gap-5 xl:max-w-[380px] w-full order-first xl:order-none">
            <WalletStack />

        {/* The whole chat lives inside one receipt: header -> body (greeting OR thread) -> composer -> perforated edge */}
        <div
          className="rounded-2xl overflow-hidden"
          style={{ background: "var(--purch-paper)", boxShadow: "var(--purch-shadow-sm)" }}
        >
          <div className="flex items-center justify-between px-5 pt-3">
            <h2 className="font-sans font-semibold text-[13px] text-[color:var(--purch-muted-ink)]">
              Assistant
            </h2>
            <button
              onClick={clearChat}
              disabled={!hasStarted}
              className="p-1.5 rounded-lg disabled:opacity-30 transition-opacity hover:bg-gray-100"
              style={{ color: "#000000" }}
            >
              <Trash2 size={15} style={{ color: "#000000", border: "1px solid #000000", borderRadius: "4px" }} />
            </button>
          </div>

          <div className="px-5 py-4">
            {!hasStarted ? (
              /* Empty state: gradient avatar + greeting + chips */
              <div className="flex flex-col items-center justify-center text-center pt-2 pb-6">
                {/* Gradient orb avatar */}
                <div
                  className="w-16 h-16 rounded-full flex items-center justify-center mb-4"
                  style={{ background: "radial-gradient(circle at 30% 25%, rgba(255,255,255,0.4) 0%, transparent 25%), radial-gradient(circle at 35% 30%, #5B21B6 0%, #3E0F8D 45%, #2D0A6E 100%)", }}
                >
                  <span className="text-[28px] font-sans font-bold text-white leading-none">P</span>
                </div>
                <h2 className="font-sans font-extrabold text-[32px] tracking-tight mt-0 mb-3 m-0 leading-tight" style={{ minHeight: "2.5em" }}>
                  {greetingText}
                  {greetingText.length < greetingFull.length && <span className="inline-block w-[3px] h-[0.85em] ml-0.5 align-baseline" style={{ background: "var(--purch-accent)", animation: "blink 0.6s step-end infinite" }} />}
                </h2>
                <div className="flex flex-wrap gap-2 justify-center mt-2">
                  {PROMPT_CHIPS.map((c, i) => (
                    <button
                      key={c}
                      onClick={() => {
                        setDraft(c);
                        inputRef.current?.focus();
                      }}
                      className={`text-[12.5px] px-3.5 py-1.5 rounded-full cursor-pointer transition-all duration-300 ${i >= 2 ? "md:hidden" : ""}`}
                      style={{
                        border: "1px solid var(--purch-line)",
                        background: "#FFFFFF",
                        color: "var(--purch-ink)",
                        opacity: greetingDone ? 1 : 0,
                        transform: greetingDone ? "translateY(0)" : "translateY(8px)",
                        transitionDelay: `${greetingDone ? (i + 1) * 100 : 0}ms`,
                      }}
                    >
                      {c}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              /* Thread — fixed responsive height that fits the viewport so the
                 page itself doesn't scroll; only the conversation scrolls. */
              <div className="h-[calc(100dvh-420px)] md:h-[calc(100dvh-460px)] lg:h-[calc(100dvh-470px)] overflow-y-auto">
                {messages.map((m, i) =>
                  m.role === "user" ? (
                    <div key={i} className="flex justify-end py-2.5">
                      <div className="purch-bubble-user max-w-[78%]">{m.text}</div>
                    </div>
                  ) : (
                    <div key={i} className="flex items-start gap-2.5 py-2.5">
                      <div
                        className="mt-0.5 w-7 h-7 shrink-0 rounded-full flex items-center justify-center"
                        style={{ background: "radial-gradient(circle at 30% 25%, rgba(255,255,255,0.4) 0%, transparent 25%), radial-gradient(circle at 35% 30%, #5B21B6 0%, #3E0F8D 45%, #2D0A6E 100%)", }}
                      >
                        <span className="font-sans font-bold text-[11px] text-white">P</span>
                      </div>
                      <div className="flex-1">
                        <ReceiptLine>
                          {m.alert === "warning" && (
                            <span className="font-bold uppercase text-[0.65rem] tracking-[0.1em] mr-1" style={{ color: "var(--purch-gold)" }}>
                              <AlertTriangle size={12} strokeWidth={1.5} className="inline-block mr-1" />Budget warning —{" "}
                            </span>
                          )}
                          {m.alert === "danger" && (
                            <span className="font-bold uppercase text-[0.65rem] tracking-[0.1em] mr-1" style={{ color: "var(--purch-rust)" }}>
                              <AlertTriangle size={12} strokeWidth={1.5} className="inline-block mr-1" />Over budget —{" "}
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
                      className="mt-0.5 w-7 h-7 shrink-0 rounded-full flex items-center justify-center"
                      style={{ background: "radial-gradient(circle at 30% 25%, rgba(255,255,255,0.4) 0%, transparent 25%), radial-gradient(circle at 35% 30%, #5B21B6 0%, #3E0F8D 45%, #2D0A6E 100%)", }}
                    >
                      <span className="font-sans font-bold text-[11px] text-white">P</span>
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
            <div className="px-5 pb-4">
              {/* Combined input area — larger, tone selector inside */}
              <div className="rounded-xl border overflow-hidden flex flex-col" style={{ border: "1px solid var(--purch-line-soft)", background: "#FFFFFF" }}>
                <textarea
                  ref={inputRef}
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  disabled={busy}
                  onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
                  placeholder="What would you like to track?"
                  rows={2}
                  className="flex-1 px-4 pt-3 pb-1 text-[14px] disabled:opacity-60 bg-transparent outline-none border-none resize-none min-h-[60px]"
                />
                <div className="flex items-center justify-between px-3 py-2" style={{ borderTop: "1px solid var(--purch-line-soft)" }}>
                  <select
                    value={tone}
                    onChange={(e) => changeTone(e.target.value)}
                    className="text-[11px] font-medium px-2 py-1 rounded-md outline-none cursor-pointer"
                    style={{ background: "#242424", color: "#FFFFFF", border: "none" }}
                  >
                    {TONE_OPTIONS.map((t) => (
                      <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
                    ))}
                  </select>
                  <button
                    onClick={() => send()}
                    disabled={busy}
                    className="flex items-center justify-center w-8 h-8 rounded-full shrink-0 transition-colors hover:bg-gray-100 disabled:opacity-40"
                    style={{ background: "transparent" }}
                  >
                    <Send size={14} style={{ color: "var(--purch-ink)" }} />
                  </button>
                </div>
              </div>
            </div>
          )}

          <PerforatedEdge />
        </div>
      </div>
    </div>
  </div>
    </PageShell>
  );
}
