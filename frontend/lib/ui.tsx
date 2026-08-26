"use client";

import Link from "next/link";

// Shared class fragments mirroring purch.theme.CLASSES, so the whole app
// references palette tokens by name instead of hard-coding hex values.

export const pageClass =
  "min-h-screen w-full bg-[color:var(--purch-parchment)] text-[color:var(--purch-ink)]";

export const cardClass =
  "bg-[color:var(--purch-paper)] border border-[color:var(--purch-border)] rounded-2xl shadow-sm";

export const displayHeading =
  "font-['Playfair_Display'] font-bold tracking-tight text-[color:var(--purch-ink)]";

export const eyebrow =
  "font-['DM_Mono'] text-[0.65rem] uppercase tracking-[0.12em] text-[color:var(--purch-muted)]";

export const primaryButton =
  "inline-flex items-center justify-center gap-2 rounded-xl " +
  "bg-[color:var(--purch-coral)] hover:bg-[color:var(--purch-coral-light)] " +
  "text-white font-semibold px-4 py-2.5 transition-colors " +
  "shadow-[0_4px_14px_var(--purch-coral-shadow)]";

export const outlineButton =
  "inline-flex items-center justify-center gap-2 rounded-xl " +
  "border border-[color:var(--purch-border)] bg-[color:var(--purch-paper)] " +
  "text-[color:var(--purch-ink)] hover:border-[color:var(--purch-coral)] " +
  "hover:text-[color:var(--purch-coral)] font-medium px-4 py-2 transition-colors";

export const ghostButton =
  "inline-flex items-center justify-center gap-2 rounded-xl " +
  "text-[color:var(--purch-muted)] hover:text-[color:var(--purch-coral)] " +
  "font-medium px-3 py-2 transition-colors";

export const TONES = [
  "Nonchalant",
  "Bestie",
  "Sarcastic",
  "Coach",
  "Rich Tita",
  "Kapampangan",
];

export function Brand({
  size = "md",
  showBeta = true,
}: {
  size?: "sm" | "md" | "lg";
  showBeta?: boolean;
}) {
  const sizeCls =
    size === "lg" ? "text-4xl" : size === "sm" ? "text-xl" : "text-2xl";
  return (
    <div className="flex items-center gap-2">
      <span
        className={`${sizeCls} font-['Playfair_Display'] font-bold text-[color:var(--purch-gold)]`}
      >
        Purch
      </span>
      {showBeta && <span className="purch-beta-badge">Beta</span>}
    </div>
  );
}

export function ToneChip({ tone }: { tone: string }) {
  return <span className="purch-chip">{tone}</span>;
}

const NAV = [
  { href: "/chat", label: "Chat", icon: "💬" },
  { href: "/wallets", label: "Wallets", icon: "👛" },
  { href: "/analytics", label: "Analytics", icon: "📊" },
];

export function Sidebar({ active }: { active?: string }) {
  return (
    <aside className="hidden sm:flex w-60 shrink-0 flex-col border-r border-[color:var(--purch-border)] bg-[color:var(--purch-dark)] text-[color:var(--purch-parchment)] p-4">
      <Link href="/" className="mb-8">
        <Brand showBeta={false} />
      </Link>
      <nav className="flex flex-col gap-1">
        {NAV.map((item) => {
          const isActive = active === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={
                "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors " +
                (isActive
                  ? "bg-[color:var(--purch-dark-mid)] text-[color:var(--purch-coral-light)]"
                  : "text-[color:var(--purch-parchment)] opacity-80 hover:bg-[color:var(--purch-dark-mid)] hover:opacity-100")
              }
            >
              <span aria-hidden>{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="mt-auto pt-4 text-xs text-[color:var(--purch-muted)]">
        Budget tracking,
        <br />
        reimagined.
      </div>
    </aside>
  );
}

export function MobileNav({ active }: { active?: string }) {
  return (
    <nav className="sm:hidden fixed bottom-0 inset-x-0 z-20 flex border-t border-[color:var(--purch-border)] bg-[color:var(--purch-paper)]">
      {NAV.map((item) => {
        const isActive = active === item.href;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={
              "flex-1 flex flex-col items-center gap-0.5 py-2 text-[0.65rem] font-medium " +
              (isActive
                ? "text-[color:var(--purch-coral)]"
                : "text-[color:var(--purch-muted)]")
            }
          >
            <span aria-hidden className="text-lg">
              {item.icon}
            </span>
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

export function PageShell({
  children,
  active,
}: {
  children: React.ReactNode;
  active?: string;
}) {
  return (
    <div className="flex min-h-screen">
      <Sidebar active={active} />
      <main className="flex-1 min-w-0 pb-16 sm:pb-0">{children}</main>
      <MobileNav active={active} />
    </div>
  );
}
