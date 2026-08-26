import Link from "next/link";
import { Brand, ToneChip, primaryButton, outlineButton, eyebrow } from "@/lib/ui";

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
    <main className="min-h-screen w-full bg-[color:var(--purch-parchment)] text-[color:var(--purch-ink)]">
      <div className="grid grid-cols-1 lg:grid-cols-2 w-full min-h-screen">
        {/* Hero */}
        <section className="bg-[color:var(--purch-dark)] flex items-center">
          <div className="flex flex-col justify-center gap-5 w-full px-6 sm:px-10 lg:px-16 py-16 lg:py-20">
            <Brand size="lg" showBeta={false} />
            <div className={eyebrow}>Budget tracking, reimagined</div>
            <h1 className="font-['Playfair_Display'] font-bold text-5xl sm:text-6xl lg:text-7xl leading-[1.02] mt-3 text-[color:var(--purch-parchment)]">
              Your last{" "}
              <em className="italic text-[color:var(--purch-coral-light)]">
                eventually
              </em>
              <br />
              leads to another.
            </h1>
            <p className="mt-5 max-w-xl text-[color:var(--purch-muted)] leading-relaxed">
              Log expenses the way you text — casually. Purch extracts the item,
              amount, and category, and reacts in the tone you pick. No forms,
              no dropdowns — just chat.
            </p>
            <div className="flex flex-wrap gap-2 mt-6">
              {TONE_CHIPS.map((t) => (
                <ToneChip key={t} tone={t} />
              ))}
            </div>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link href="/chat" className={primaryButton}>
                Open the chat →
              </Link>
              <Link
                href="/login"
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-[color:var(--purch-border)]/40 text-[color:var(--purch-parchment)] hover:border-[color:var(--purch-coral-light)] hover:text-[color:var(--purch-coral-light)] font-medium px-4 py-2.5 transition-colors"
              >
                Sign in
              </Link>
            </div>
          </div>
        </section>

        {/* Preview card + showcase */}
        <section className="bg-[color:var(--purch-parchment)] flex flex-col items-center justify-center px-6 sm:px-10 lg:px-16 py-16">
          <div className="w-full max-w-md border border-[color:var(--purch-border)] rounded-2xl overflow-hidden shadow-[var(--purch-shadow-md)]">
            <div className="flex items-center justify-between bg-[color:var(--purch-dark)] px-4 py-2">
              <span className="font-['DM_Mono'] text-[0.7rem] text-[color:var(--purch-gold)]">
                PURCH RECEIPT
              </span>
              <span className="font-['DM_Mono'] text-[0.7rem] text-[color:var(--purch-muted)]">
                ✨ Bestie
              </span>
            </div>
            <div className="bg-[color:var(--purch-paper)] p-5">
              <div className="flex justify-end mb-3">
                <div className="purch-bubble-user text-sm max-w-[80%]">
                  bought a phone case for 350
                </div>
              </div>
              <div className="flex justify-start mb-3">
                <div className="purch-bubble-assistant text-sm max-w-[80%]">
                  Logged! Phone case ₱350 under Shopping. 🛍️
                </div>
              </div>
              <div className="flex justify-end mb-3">
                <div className="purch-bubble-user text-sm max-w-[80%]">
                  how much this week?
                </div>
              </div>
              <div className="flex justify-start">
                <div className="purch-bubble-assistant text-sm max-w-[80%]">
                  You spent ₱2,450 this week — most of it on Food. 🍽️
                </div>
              </div>
            </div>
          </div>

          <div className="purch-card p-6 mt-6 w-full max-w-md">
            <h2 className="font-['Playfair_Display'] font-bold text-2xl text-[color:var(--purch-ink)]">
              Own it. Log it.
            </h2>
            <p className="text-sm text-[color:var(--purch-secondary-text)] mt-1">
              Whether it&apos;s your first expense or your thousandth, Purch is
              ready when you are.
            </p>
            <Link
              href="/login"
              className={`${primaryButton} mt-4 w-full`}
            >
              Start tracking
            </Link>
          </div>
        </section>
      </div>
    </main>
  );
}
