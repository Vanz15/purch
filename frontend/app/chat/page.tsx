"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { api, ChatMessage, ChatResponse } from "@/lib/api";
import {
  PageShell,
  eyebrow,
  displayHeading,
  primaryButton,
  outlineButton,
} from "@/lib/ui";
import { PerforatedEdge, ReceiptHeader } from "@/lib/receipt";

const PROMPT_CHIPS = [
  "milk tea 85 gcash",
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

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getSession().then(({ data }) => {
      setAuthed(!!data.session);
      setReady(true);
    });
  }, []);

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
            <h3 className={`${displayHeading} text-2xl mt-0 mb-3 m-0`}>
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
      <div className="mx-auto max-w-[640px]">
        <div className={eyebrow}>Chat</div>
        <h1 className="font-['Fraunces'] font-semibold text-[30px] mt-0 mb-5 m-0">
          Talk to Purch
        </h1>

        {error && (
          <div className="flex items-center gap-3 mb-4 p-3 rounded-lg border" style={{ borderColor: "var(--purch-rust)", background: "var(--purch-paper)" }}>
            <span className="font-bold" style={{ color: "var(--purch-rust)" }}>⚠</span>
            <p className="text-sm flex-1 m-0">{error}</p>
          </div>
        )}

        {/* Receipt-styled chat thread */}
        <div
          className="rounded-md overflow-hidden"
          style={{ background: "var(--purch-paper)", boxShadow: "var(--purch-shadow-sm)" }}
        >
          <ReceiptHeader title="Live receipt" tone="Neutral" />
          <div className="px-5 py-1 max-h-[360px] overflow-y-auto">
            {hasMessages ? (
              messages.map((m, i) =>
                m.role === "user" ? (
                  <div key={i} className="flex justify-end py-2.5">
                    <div className="purch-bubble-user max-w-[75%]">{m.text}</div>
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
              )
            ) : (
              <div className="py-6 text-center text-[color:var(--purch-taupe)] text-sm">
                Say something like “lunch 80 baon” and Purch logs it as a receipt line.
              </div>
            )}
            {busy && (
              <ReceiptLine>
                <span className="opacity-60">Purch is writing…</span>
              </ReceiptLine>
            )}
            <div ref={endRef} />
          </div>
          <PerforatedEdge />
        </div>

        {/* Wallet choice row */}
        {awaitingWallet && (
          <div className="mt-4 p-4 rounded-lg border border-dashed" style={{ borderColor: "var(--purch-line)" }}>
            <div className={eyebrow}>Pick a wallet — required</div>
            <div className="flex flex-wrap gap-2 mt-2">
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
        )}

        {/* Prompt chips */}
        <div className="flex flex-wrap gap-2 my-4">
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

        {/* Composer */}
        <div className="flex gap-2.5">
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            disabled={busy || awaitingWallet}
            onKeyDown={(e) => e.key === "Enter" && send()}
            placeholder='Try "milk tea ₱85" or "how much this week?"'
            className="flex-1 px-4 py-3.5 rounded-lg text-[14px] bg-[color:var(--purch-paper)] disabled:opacity-60"
            style={{ border: "1px solid var(--purch-line-soft)" }}
          />
          <button
            onClick={() => send()}
            disabled={busy || awaitingWallet}
            className={`${primaryButton} px-6 disabled:opacity-60`}
          >
            Send
          </button>
        </div>
      </div>
    </PageShell>
  );
}
