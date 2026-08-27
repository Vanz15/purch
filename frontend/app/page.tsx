"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Brand, ToneChip } from "@/lib/ui";
import { PerforatedEdge, ReceiptHeader } from "@/lib/receipt";
import { createClient } from "@/lib/supabase/client";

const TONE_CHIPS = [
  "Nonchalant",
  "Bestie",
  "Sarcastic",
  "Coach",
  "Rich Tita",
  "Kapampangan",
];

function GoogleLogo() {
  return (
    <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
    </svg>
  );
}

export default function LandingPage() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) router.replace("/chat");
    });
  }, [router]);

  async function signInWithGoogle() {
    setBusy(true);
    const supabase = createClient();
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${location.origin}/auth/callback` },
    });
    if (error) {
      console.error(error.message);
      setBusy(false);
    }
  }

  function signInAsGuest() {
    const uuid = crypto.randomUUID().replace(/-/g, "").slice(0, 12);
    const guestEmail = `guest-${uuid}@purch.local`;
    localStorage.setItem("purch_user_email", guestEmail);
    localStorage.setItem("purch_user_name", `Guest ${uuid.slice(0, 6)}`);
    localStorage.setItem("purch_auth_method", "guest");
    router.replace("/chat");
  }

  return (
    <main className="grid grid-cols-1 lg:grid-cols-2 min-h-screen font-['Inter']">
      {/* Left hero — espresso */}
      <section
        className="flex flex-col justify-center px-12 py-14"
        style={{ background: "var(--purch-ink)", color: "var(--purch-paper)" }}
      >
        <div className="purch-fade-up" style={{ ["--i" as string]: 0 }}>
          <Brand showBeta={false} />
          <div className="text-[11px] uppercase tracking-[0.15em] text-[color:var(--purch-taupe)] mt-1.5 mb-7">
            Budget tracking, reimagined
          </div>
        </div>

        <h1
          className="font-['Fraunces'] font-semibold text-[46px] leading-[1.08] mt-0 mb-5 m-0 purch-fade-up"
          style={{ ["--i" as string]: 1 }}
        >
          Your last{" "}
          <em className="italic" style={{ color: "var(--purch-rust)" }}>
            eventually
          </em>{" "}
          leads to another.
        </h1>

        <p
          className="text-[15px] leading-relaxed text-[#D8CFC2] max-w-[420px] mb-7 purch-fade-up"
          style={{ ["--i" as string]: 2 }}
        >
          Text it like you&apos;d text a friend. Purch reads the item, the peso,
          and the wallet — no forms, no dropdowns, no app to learn.
        </p>

        <div
          className="flex flex-wrap gap-2 mb-8 purch-fade-up"
          style={{ ["--i" as string]: 3 }}
        >
          {TONE_CHIPS.map((t) => (
            <ToneChip key={t} tone={t} />
          ))}
        </div>

        {/* Auth actions — replaced the old /login CTA links */}
        <div
          className="flex flex-col gap-3 max-w-[420px] purch-fade-up"
          style={{ ["--i" as string]: 4 }}
        >
          <button
            onClick={signInWithGoogle}
            disabled={busy}
            className="inline-flex items-center justify-center gap-3 rounded-lg bg-[color:var(--purch-paper)] text-[color:var(--purch-ink)] font-semibold px-5 py-3 transition-opacity hover:opacity-90 disabled:opacity-60"
          >
            <GoogleLogo />
            {busy ? "Please wait…" : "Continue with Google"}
          </button>

          <button
            onClick={signInAsGuest}
            className="inline-flex items-center justify-center gap-2 rounded-lg border px-5 py-3 text-[14px] font-semibold transition-colors purch-cta-pulse"
            style={{
              background: "transparent",
              color: "var(--purch-paper)",
              borderColor: "var(--purch-taupe)",
            }}
          >
            Continue as Guest
          </button>

          <p className="text-[12px] text-[#9a8f7e] mt-1">
            Guest mode keeps your session on this device only.
          </p>
        </div>
      </section>

      {/* Right — cream showcase */}
      <section
        className="flex flex-col justify-center gap-5 p-10"
        style={{ background: "var(--purch-bg)" }}
      >
        <div
          className="rounded overflow-hidden purch-float"
          style={{
            background: "var(--purch-paper)",
            boxShadow: "var(--purch-shadow-md)",
          }}
        >
          <ReceiptHeader title="Purch receipt" tone="Bestie" />
          <div className="px-5 pb-5 pt-4">
            <div className="flex justify-end mb-3.5">
              <div className="purch-bubble-user">
                bought a phone case for 350
              </div>
            </div>
            <div className="purch-receipt-line">
              Logged. Phone case —{" "}
              <b className="font-['JetBrains_Mono']">₱350.00</b> under Shopping.
              Bestie&apos;s proud of you for tracking it, at least.
            </div>
            <div className="flex justify-end mb-3.5">
              <div className="purch-bubble-user">how much this week?</div>
            </div>
            <div className="purch-receipt-line">
              <span className="font-['JetBrains_Mono'] font-bold">₱2,450.00</span>{" "}
              this week — most of it on Food.
            </div>
          </div>
          <PerforatedEdge />
        </div>

        <div
          className="rounded-lg p-6"
          style={{
            background: "var(--purch-paper)",
            boxShadow: "var(--purch-shadow-sm)",
          }}
        >
          <h3 className="font-['Fraunces'] font-semibold text-xl mt-0 mb-1.5 m-0">
            Own it. Log it.
          </h3>
          <p className="text-[13px] text-[color:var(--purch-taupe)] mb-4 leading-relaxed m-0">
            Whether it&apos;s your first expense or your thousandth, Purch is
            ready when you are.
          </p>
          <Link
            href="/chat"
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-[color:var(--purch-rust)] hover:opacity-90 text-[color:var(--purch-paper)] font-semibold px-4 py-2.5 transition-opacity w-full"
          >
            Start tracking <ArrowRight size={16} />
          </Link>
        </div>
      </section>
    </main>
  );
}
