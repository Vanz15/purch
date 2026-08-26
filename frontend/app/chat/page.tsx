"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { api, ChatMessage, ChatResponse } from "@/lib/api";
import { PageShell, eyebrow, displayHeading, primaryButton, outlineButton } from "@/lib/ui";

const PROMPT_CHIPS = [
  "coffee 150 cash",
  "lent 500 to Maria",
  "how much this week?",
  "set food budget 3000",
];

function AssistantAvatar() {
  return (
    <div className="w-8 h-8 rounded-full bg-[color:var(--purch-dark)] text-[color:var(--purch-gold)] font-['Playfair_Display'] font-bold text-sm flex items-center justify-center flex-shrink-0 mt-0.5">
      P
    </div>
  );
}

function AlertHeader({ alert }: { alert: string }) {
  if (alert === "warning")
    return (
      <div className="flex items-center gap-1.5 font-['Playfair_Display'] font-bold text-[0.65rem] uppercase tracking-[0.1em] mb-2 text-[color:var(--purch-gold)]">
        <span>⚠</span>
        <span>Budget warning</span>
      </div>
    );
  if (alert === "danger")
    return (
      <div className="flex items-center gap-1.5 font-['Playfair_Display'] font-bold text-[0.65rem] uppercase tracking-[0.1em] mb-2 text-[color:var(--purch-danger)]">
        <span>⚠</span>
        <span>Over budget</span>
      </div>
    );
  return null;
}

function Message({ msg }: { msg: ChatMessage }) {
  if (msg.role === "user") {
    return (
      <div className="mb-4 flex flex-col items-end ml-auto self-end max-w-[92%] sm:max-w-[85%] lg:max-w-[80%] min-w-0">
        <div className="purch-bubble-user">
          <p className="text-[0.9rem] leading-relaxed whitespace-pre-wrap m-0">
            {msg.text}
          </p>
        </div>
        <div className="text-xs text-[color:var(--purch-muted)] mt-1.5 mr-1 text-right">
          {msg.time}
        </div>
      </div>
    );
  }
  const bubbleCls =
    msg.alert === "warning"
      ? "purch-bubble-assistant border-2 border-[color:var(--purch-gold)]"
      : msg.alert === "danger"
      ? "purch-bubble-assistant border-2 border-[color:var(--purch-danger)]"
      : "purch-bubble-assistant";
  return (
    <div className="mb-4 flex justify-start items-start gap-2">
      <AssistantAvatar />
      <div className="max-w-[92%] sm:max-w-[85%] lg:max-w-[80%] min-w-0">
        <div className={bubbleCls}>
          <AlertHeader alert={msg.alert} />
          <p className="text-base leading-7 whitespace-pre-wrap m-0">{msg.text}</p>
          {msg.meta && (
            <div className="mt-2 pt-2 border-t border-dashed border-[color:var(--purch-border)] font-['DM_Mono'] text-xs text-[color:var(--purch-muted)]">
              {msg.meta}
            </div>
          )}
        </div>
        <div className="text-xs text-[color:var(--purch-muted)] mt-1.5 ml-1">
          {msg.time}
        </div>
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="mb-4 flex justify-start items-center gap-2">
      <AssistantAvatar />
      <div className="purch-bubble-assistant flex items-center gap-1.5 py-3">
        <span className="w-1.5 h-1.5 rounded-full bg-[color:var(--purch-muted)] animate-pulse" />
        <span className="w-1.5 h-1.5 rounded-full bg-[color:var(--purch-muted)] animate-pulse [animation-delay:150ms]" />
        <span className="w-1.5 h-1.5 rounded-full bg-[color:var(--purch-muted)] animate-pulse [animation-delay:300ms]" />
      </div>
    </div>
  );
}

export default function ChatPage() {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [authed, setAuthed] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  // Phase 3 client-side conversational state (Option A statelessness)
  const [pendingWallet, setPendingWallet] = useState<Record<string, any> | null>(null);
  const [walletChoices, setWalletChoices] = useState<any[]>([]);
  const [awaitingWallet, setAwaitingWallet] = useState(false);
  const [confirmClear, setConfirmClear] = useState(false);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getSession().then(({ data }) => {
      setAuthed(!!data.session);
      setReady(true);
    });
  }, []);

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
      } catch (e: any) {
        setError(e.message || "Request failed.");
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
    } catch (e: any) {
      setError(e.message || "Wallet choice failed.");
    } finally {
      setBusy(false);
    }
  }

  if (!ready) {
    return (
      <main className="min-h-screen flex items-center justify-center text-[color:var(--purch-muted)]">
        Loading…
      </main>
    );
  }

  // Unauthenticated prompt
  if (!authed) {
    return (
      <PageShell active="/chat">
        <div className="max-w-3xl mx-auto w-full p-3 sm:p-6 lg:p-8">
          <div className="purch-card p-8 flex flex-col items-center justify-center py-12 sm:py-16 text-center">
            <div className="w-16 h-16 rounded-2xl bg-[color:var(--purch-dark)] text-[color:var(--purch-gold)] font-['Playfair_Display'] font-bold text-3xl flex items-center justify-center">
              P
            </div>
            <h3 className={`${displayHeading} text-2xl mt-4`}>Sign in to start chatting.</h3>
            <p className="text-base text-[color:var(--purch-muted)] mt-3 max-w-md leading-relaxed">
              Purch keeps every purchase, budget, and tone tied to your account.
              Sign in with Google or email — or continue as a guest to preview
              the experience privately on this device.
            </p>
            <div className="flex flex-wrap items-center justify-center gap-3 mt-6">
              <a href="/login" className={primaryButton}>
                Sign in
              </a>
              <button
                onClick={() => {
                  const uuid = crypto.randomUUID().replace(/-/g, "").slice(0, 12);
                  localStorage.setItem("purch_user_email", `guest-${uuid}@purch.local`);
                  localStorage.setItem("purch_user_name", `Guest ${uuid.slice(0, 6)}`);
                  localStorage.setItem("purch_auth_method", "guest");
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

  const hasMessages = messages.length > 0;

  return (
    <PageShell active="/chat">
      <div className="max-w-3xl mx-auto w-full p-3 sm:p-6 lg:p-8">
        {/* Header + clear */}
        <div className="flex items-start justify-between gap-3 mb-4">
          <div className="flex-1 min-w-0">
            <div className={eyebrow}>Chat</div>
            <h2 className={`${displayHeading} text-2xl sm:text-3xl mt-1`}>Talk to Purch</h2>
          </div>
          {hasMessages &&
            (confirmClear ? (
              <div className="flex items-center gap-2">
                <span className="text-xs text-[color:var(--purch-muted)] mr-1">Clear conversation?</span>
                <button onClick={() => { setMessages([]); setConfirmClear(false); }} className={`${outlineButton} text-xs py-1.5 px-3`}>
                  Confirm
                </button>
                <button onClick={() => setConfirmClear(false)} className={`${outlineButton} text-xs py-1.5 px-3`}>
                  Cancel
                </button>
              </div>
            ) : (
              <button onClick={() => setConfirmClear(true)} className="text-xs text-[color:var(--purch-muted)] hover:text-[color:var(--purch-coral)] transition-colors">
                ↺ Clear chat
              </button>
            ))}
        </div>

        {/* Error banner */}
        {error && (
          <div className="flex items-center gap-3 mb-3 p-3 rounded-xl border border-[color:var(--purch-danger)] bg-[color:var(--purch-paper)]">
            <span className="text-[color:var(--purch-danger)] font-bold">⚠</span>
            <p className="text-sm text-[color:var(--purch-ink)] flex-1 m-0">{error}</p>
            <button onClick={() => setError("")} className="text-xs text-[color:var(--purch-muted)] hover:text-[color:var(--purch-ink)] transition-colors">
              Dismiss
            </button>
          </div>
        )}

        {/* Messages or empty state */}
        {hasMessages ? (
          <div className="flex flex-col py-4 min-h-[300px]">
            {messages.map((m, i) => (
              <Message key={i} msg={m} />
            ))}
            {busy && <TypingIndicator />}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-12 sm:py-16">
            <div className="w-16 h-16 rounded-2xl bg-[color:var(--purch-dark)] text-[color:var(--purch-gold)] font-['Playfair_Display'] font-bold text-3xl flex items-center justify-center purch-rise" />
            <h3 className={`${displayHeading} text-xl mt-4`}>Hey! I&apos;m Purch.</h3>
            <p className="text-base text-[color:var(--purch-muted)] mt-3 max-w-md text-center leading-relaxed">
              Tell me what you bought and which wallet it came from, log what you
              borrowed or lent, ask what you spent, or set a budget. No forms,
              no dropdowns — just a quick, natural chat.
            </p>
            <div className="flex flex-wrap justify-center gap-2 mt-6 max-w-md">
              {PROMPT_CHIPS.map((p) => (
                <button
                  key={p}
                  onClick={() => send(p)}
                  className="px-3.5 py-2 rounded-full text-sm font-semibold bg-[color:var(--purch-paper)] border border-[color:var(--purch-border)] text-[color:var(--purch-ink)] hover:border-[color:var(--purch-coral)] hover:text-[color:var(--purch-coral)] transition-colors"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Wallet choice row */}
        {awaitingWallet && (
          <div className="mt-2 p-4 rounded-xl border border-dashed border-[color:var(--purch-border)] bg-[color:var(--purch-parchment)]">
            <div className={eyebrow}>Pick a wallet — required</div>
            <div className="flex flex-wrap gap-2 mt-2">
              {walletChoices.map((w) => (
                <button
                  key={w.id}
                  onClick={() => chooseWallet(w.id)}
                  className="flex flex-col items-start gap-0.5 px-3.5 py-2 rounded-xl bg-[color:var(--purch-paper)] border border-[color:var(--purch-border)] text-[color:var(--purch-ink)] hover:border-[color:var(--purch-teal)] hover:text-[color:var(--purch-teal)] transition-colors"
                >
                  <span className="text-sm font-semibold">{w.name}</span>
                  <span className="font-['DM_Mono'] text-[0.65rem] text-[color:var(--purch-muted)]">
                    {w.wallet_type} · ₱{w.balance_display}
                  </span>
                </button>
              ))}
            </div>
            <p className="text-xs text-[color:var(--purch-muted)] mt-3 m-0">
              Every purchase needs a wallet so your balances stay accurate.
            </p>
          </div>
        )}

        {/* Composer */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send();
          }}
          className="mt-4"
        >
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              disabled={busy || awaitingWallet}
              placeholder='Try "milk tea ₱85" or "how much this week?"'
              autoComplete="off"
              className="flex-1 rounded-xl border border-[color:var(--purch-border)] bg-[color:var(--purch-paper)] px-4 py-3.5 text-base placeholder:text-[color:var(--purch-muted)] focus:outline-none focus:border-[color:var(--purch-coral)] disabled:opacity-60 disabled:cursor-not-allowed w-full min-w-0 sm:flex-1"
            />
            <button
              type="submit"
              disabled={busy || awaitingWallet}
              className={`${primaryButton} min-w-[6.5rem] text-base disabled:opacity-60 disabled:cursor-not-allowed w-full sm:w-auto sm:shrink-0`}
            >
              {busy ? "Sending…" : "Send"}
            </button>
          </div>
        </form>
      </div>
    </PageShell>
  );
}
