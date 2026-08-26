"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { api, ChatMessage, ChatResponse } from "@/lib/api";

export default function ChatPage() {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  // Phase 3 client-side conversational state (Option A statelessness)
  const [pendingWallet, setPendingWallet] = useState<Record<string, any> | null>(
    null
  );
  const [walletChoices, setWalletChoices] = useState<any[]>([]);
  const [awaitingWallet, setAwaitingWallet] = useState(false);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getSession().then(({ data }) => {
      if (!data.session) {
        router.replace("/login");
      } else {
        setReady(true);
      }
    });
  }, [router]);

  async function send() {
    const text = draft.trim();
    if (!text || busy) return;
    setBusy(true);
    setError("");
    setDraft("");
    const userMsg: ChatMessage = {
      role: "user",
      text,
      meta: "",
      time: new Date().toLocaleTimeString(),
      alert: "",
    };
    setMessages((m) => [...m, userMsg]);

    try {
      const res: ChatResponse = await api.chat.send({
        message: text,
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
          time: new Date().toLocaleTimeString(),
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
  }

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
          time: new Date().toLocaleTimeString(),
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
      <main className="min-h-screen flex items-center justify-center text-[#8a7c6b]">
        Loading…
      </main>
    );
  }

  return (
    <main className="min-h-screen flex flex-col bg-[#faf6ef]">
      <header className="p-4 border-b border-[#e7ddd0] text-[#2b2118] font-bold">
        Purch · Chat
      </header>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((m, i) => (
          <div
            key={i}
            className={m.role === "user" ? "text-right" : "text-left"}
          >
            <div
              className={
                m.role === "user"
                  ? "inline-block bg-[#2b2118] text-white rounded-2xl px-4 py-2 max-w-[80%]"
                  : "inline-block bg-white border border-[#e7ddd0] rounded-2xl px-4 py-2 max-w-[80%]"
              }
            >
              {m.text}
              {m.meta && (
                <div className="text-xs opacity-70 mt-1">{m.meta}</div>
              )}
            </div>
          </div>
        ))}

        {awaitingWallet && (
          <div className="flex flex-wrap gap-2">
            {walletChoices.map((w) => (
              <button
                key={w.id}
                onClick={() => chooseWallet(w.id)}
                className="rounded-xl border border-[#e36b5e] text-[#2b2118] px-4 py-2 text-sm"
              >
                {w.name} ({w.wallet_type}) · ₱{w.balance_display}
              </button>
            ))}
          </div>
        )}

        {error && (
          <div className="text-sm text-[#e36b5e]">⚠ {error}</div>
        )}
      </div>

      <div className="p-4 border-t border-[#e7ddd0] flex gap-2">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          disabled={busy || awaitingWallet}
          placeholder={
            awaitingWallet
              ? "Pick a wallet above first…"
              : "e.g. coffee 150 cash"
          }
          className="flex-1 rounded-xl border border-[#e7ddd0] bg-white px-3.5 py-2.5 text-sm disabled:opacity-60"
        />
        <button
          onClick={send}
          disabled={busy || awaitingWallet}
          className="rounded-xl bg-[#e36b5e] text-white px-5 py-2.5 font-medium disabled:opacity-60"
        >
          Send
        </button>
      </div>
    </main>
  );
}
