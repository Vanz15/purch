import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Brand, ToneChip, primaryButton, outlineButton } from "@/lib/ui";
import { PerforatedEdge, ReceiptHeader } from "@/lib/receipt";

const TONE_CHIPS = [
  "Nonchalant",
  "Bestie",
  "Sarcastic",
  "Coach",
  "Rich Tita",
  "Kapampangan",
];

export default function LandingPage() {
  return (
    <main className="grid grid-cols-1 lg:grid-cols-2 min-h-screen font-['Inter']">
      {/* Left hero — espresso */}
      <section
        className="flex flex-col justify-center px-12 py-14"
        style={{ background: "var(--purch-ink)", color: "var(--purch-paper)" }}
      >
        <Brand showBeta={false} />
        <div className="text-[11px] uppercase tracking-[0.15em] text-[color:var(--purch-taupe)] mt-1.5 mb-7">
          Budget tracking, reimagined
        </div>
        <h1 className="font-['Fraunces'] font-semibold text-[46px] leading-[1.08] mt-0 mb-5 m-0">
          Your last{" "}
          <em className="italic" style={{ color: "var(--purch-rust)" }}>
            eventually
          </em>{" "}
          leads to another.
        </h1>
        <p className="text-[15px] leading-relaxed text-[#D8CFC2] max-w-[420px] mb-7">
          Text it like you&apos;d text a friend. Purch reads the item, the peso,
          and the wallet — no forms, no dropdowns, no app to learn.
        </p>
        <div className="flex flex-wrap gap-2 mb-8">
          {TONE_CHIPS.map((t) => (
            <ToneChip key={t} tone={t} />
          ))}
        </div>
        <div className="flex gap-3">
          <Link href="/login" className={primaryButton}>
            Open the chat <ArrowRight size={16} />
          </Link>
          <Link
            href="/login"
            className="inline-flex items-center justify-center gap-2 rounded-lg border px-6 py-2.5 text-[14px] font-semibold transition-colors"
            style={{
              background: "transparent",
              color: "var(--purch-paper)",
              borderColor: "var(--purch-taupe)",
            }}
          >
            Sign in
          </Link>
        </div>
      </section>

      {/* Right — cream showcase */}
      <section
        className="flex flex-col justify-center gap-5 p-10"
        style={{ background: "var(--purch-bg)" }}
      >
        <div
          className="rounded overflow-hidden"
          style={{ background: "var(--purch-paper)", boxShadow: "var(--purch-shadow-md)" }}
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
            href="/login"
            className={`${primaryButton} w-full`}
          >
            Start tracking
          </Link>
        </div>
      </section>
    </main>
  );
}
