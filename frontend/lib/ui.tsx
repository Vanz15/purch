"use client";

import Link from "next/link";
import { MessageCircle, Wallet, BarChart3 } from "lucide-react";

// Shared class fragments matching the Purch redesign palette + type scale.

export const pageClass =
  "min-h-screen w-full bg-[color:var(--purch-bg)] text-[color:var(--purch-ink)]";

export const eyebrow =
  "text-[11px] uppercase tracking-[0.1em] text-[color:var(--purch-taupe)]";

export const displayHeading =
  "font-['Fraunces'] font-semibold tracking-tight text-[color:var(--purch-ink)]";

export const primaryButton =
  "inline-flex items-center justify-center gap-2 rounded-lg " +
  "bg-[color:var(--purch-rust)] hover:opacity-90 " +
  "text-[color:var(--purch-paper)] font-semibold px-4 py-2.5 transition-opacity";

export const outlineButton =
  "inline-flex items-center justify-center gap-2 rounded-lg " +
  "border border-[color:var(--purch-line-soft)] bg-[color:var(--purch-paper)] " +
  "text-[color:var(--purch-ink)] hover:border-[color:var(--purch-rust)] " +
  "transition-colors font-medium px-4 py-2";

export const ghostButton =
  "inline-flex items-center justify-center gap-2 rounded-lg " +
  "text-[color:var(--purch-taupe)] hover:text-[color:var(--purch-rust)] " +
  "transition-colors font-medium px-3 py-2";

export const TONES = [
  "Nonchalant",
  "Bestie",
  "Sarcastic",
  "Coach",
  "Rich Tita",
  "Kapampangan",
];

// Redesign palette (kept in sync with globals.css :root).
export const C = {
  ink: "#1C1410",
  paper: "#FAF3E7",
  rust: "#C24E2B",
  pine: "#2F6E5C",
  gold: "#E8B33D",
  taupe: "#8B7355",
};

export function Brand({
  size = "md",
  showBeta = true,
}: {
  size?: "sm" | "md" | "lg";
  showBeta?: boolean;
}) {
  const sizeCls =
    size === "lg" ? "text-[26px]" : size === "sm" ? "text-[19px]" : "text-[22px]";
  return (
    <div className="flex items-center gap-2">
      <span
        className={`${sizeCls} font-['Fraunces'] font-semibold text-[color:var(--purch-ink)]`}
      >
        Purch
      </span>
      {showBeta && (
        <span className="purch-beta-badge" style={{ background: C.pine }}>
          BETA
        </span>
      )}
    </div>
  );
}

export function ToneChip({ tone }: { tone: string }) {
  return (
    <span
      className="inline-flex items-center rounded-[20px] border px-3 py-1.5 text-xs"
      style={{ borderColor: C.taupe, color: "#D8CFC2" }}
    >
      {tone}
    </span>
  );
}

const NAV = [
  { href: "/chat", label: "Chat", icon: MessageCircle },
  { href: "/wallets", label: "Wallets", icon: Wallet },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
];

export function Sidebar({ active }: { active?: string }) {
  return (
    <aside className="hidden sm:flex w-[220px] shrink-0 flex-col gap-5 border-r border-[color:var(--purch-line)] bg-[color:var(--purch-paper)] p-5">
      <Link href="/" className="font-['Fraunces'] font-semibold text-xl text-[color:var(--purch-ink)]">
        Purch
      </Link>
      <nav className="flex flex-col gap-1">
        {NAV.map((item) => {
          const isActive = active === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={
                "flex items-center gap-2 rounded-md px-3 py-2 text-[13.5px] transition-colors " +
                (isActive
                  ? "bg-[color:var(--purch-bg)] font-semibold text-[color:var(--purch-ink)]"
                  : "text-[color:var(--purch-taupe)] hover:text-[color:var(--purch-ink)]")
              }
            >
              <Icon size={15} />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

export function MobileNav({ active }: { active?: string }) {
  return (
    <nav className="sm:hidden fixed bottom-0 inset-x-0 z-20 flex border-t border-[color:var(--purch-line)] bg-[color:var(--purch-paper)]">
      {NAV.map((item) => {
        const isActive = active === item.href;
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={
              "flex-1 flex flex-col items-center gap-0.5 py-2 text-[0.65rem] font-medium " +
              (isActive
                ? "text-[color:var(--purch-rust)]"
                : "text-[color:var(--purch-taupe)]")
            }
          >
            <Icon size={18} />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

import { useEffect, useState } from "react";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { guestName, isGuest } from "@/lib/guest";

export function PageShell({
  children,
  active,
}: {
  children: React.ReactNode;
  active?: string;
}) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [identity, setIdentity] = useState<{ label: string; isGuest: boolean }>({
    label: "",
    isGuest: false,
  });

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
        setIdentity({ label: name, isGuest: false });
      } else if (isGuest()) {
        setIdentity({ label: guestName(), isGuest: true });
      } else {
        setIdentity({ label: "Guest", isGuest: true });
      }
    });
  }, []);

  return (
    <div className="flex min-h-screen bg-[color:var(--purch-bg)]">
      {sidebarOpen && <Sidebar active={active} />}
      <main className="flex-1 min-w-0 pb-16 sm:pb-0 flex flex-col">
        <TopBar
          identity={identity}
          sidebarOpen={sidebarOpen}
          onToggleSidebar={() => setSidebarOpen((o) => !o)}
        />
        <div className="flex-1 px-6 py-8 sm:px-8">{children}</div>
      </main>
      <MobileNav active={active} />
    </div>
  );
}

function TopBar({
  identity,
  sidebarOpen,
  onToggleSidebar,
}: {
  identity: { label: string; isGuest: boolean };
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
}) {
  return (
    <header className="flex items-center justify-between border-b border-[color:var(--purch-line)] bg-[color:var(--purch-paper)] px-7 py-3.5">
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          aria-label={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
          className="hidden sm:flex items-center justify-center h-8 w-8 rounded-md text-[color:var(--purch-taupe)] hover:text-[color:var(--purch-rust)] hover:bg-[color:var(--purch-bg)] transition-colors"
        >
          {sidebarOpen ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}
        </button>
        <Brand size="sm" showBeta={false} />
      </div>
      <div className="flex items-center gap-2.5">
        {identity.label && (
          <span className="text-[13px] text-[color:var(--purch-ink)] max-w-[180px] truncate">
            {identity.label}
          </span>
        )}
        <div
          className="flex h-7 w-7 items-center justify-center rounded-full font-['Fraunces'] font-bold text-[12px]"
          style={{ background: C.ink, color: C.gold }}
        >
          P
        </div>
      </div>
    </header>
  );
}

