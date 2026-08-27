"use client";

import Link from "next/link";
import { MessageCircle, Wallet, BarChart3 } from "lucide-react";
import { createContext, useContext, useCallback, useRef, useEffect, useState, useMemo } from "react";

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
  mark = false,
}: {
  size?: "sm" | "md" | "lg";
  showBeta?: boolean;
  mark?: boolean;
}) {
  const sizeCls =
    size === "lg" ? "text-[26px]" : size === "sm" ? "text-[20px]" : "text-[22px]";
  return (
    <div className="flex items-center gap-2">
      {mark && (
        <span
          className="flex h-7 w-7 items-center justify-center rounded-lg font-['Fraunces'] font-bold text-[15px]"
          style={{ background: C.ink, color: C.gold }}
        >
          P
        </span>
      )}
      <span
        className={`${sizeCls} font-['Fraunces'] font-semibold tracking-tight text-[color:var(--purch-ink)]`}
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

import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { guestName, isGuest } from "@/lib/guest";

const NAV = [
  { href: "/chat", label: "Chat", icon: MessageCircle },
  { href: "/wallets", label: "Wallets", icon: Wallet },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
];

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
              "flex-1 flex flex-col items-center gap-0.5 py-2 text-[0.65rem] font-medium rounded-md mx-1 my-1 transition-colors " +
              (isActive
                ? "bg-[#CDBFA6] text-[color:var(--purch-ink)]"
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

export function PageShell({
  children,
  active,
  sidebar,
}: {
  children: React.ReactNode;
  active?: string;
  sidebar?: React.ReactNode;
}) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [identity, setIdentity] = useState<{ label: string; isGuest: boolean }>({
    label: "",
    isGuest: false,
  });

  // On small screens the sidebar is a slide-in drawer (closed by default);
  // on desktop it's a persistent left column (open by default).
  useEffect(() => {
    if (typeof window !== "undefined" && window.innerWidth < 1024) {
      setSidebarOpen(false);
    }
  }, []);

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
      {sidebar && (
        <>
          {/* Backdrop: click to close (mobile drawer). Hidden on desktop where
              the column collapses via the toggle button instead. */}
          <div
            className={`lg:hidden fixed inset-0 z-40 bg-black/40 transition-opacity ${
              sidebarOpen ? "opacity-100" : "opacity-0 pointer-events-none"
            }`}
            onClick={() => setSidebarOpen(false)}
          />
          {/* Sidebar: full-height sticky column on lg+ (collapses via width),
              slide-in drawer on mobile. Kept MOUNTED so toggling never resets data. */}
          <div
            className={`fixed inset-y-0 left-0 z-50 w-[300px] max-w-[85%] overflow-y-auto
              bg-[color:var(--purch-bg)] transition-[transform,width] duration-200 ease-out
              lg:static lg:inset-auto lg:z-auto lg:h-screen lg:sticky lg:top-0 lg:overflow-y-auto
              ${
                sidebarOpen
                  ? "translate-x-0 lg:w-[300px] lg:shrink-0"
                  : "-translate-x-full lg:translate-x-0 lg:w-0 lg:shrink-0 lg:overflow-hidden"
              }`}
          >
            {sidebar}
          </div>
        </>
      )}
      <main className="flex-1 min-w-0 pb-20 sm:pb-0 flex flex-col">
        <TopBar
          active={active}
          identity={identity}
          showToggle={!!sidebar}
          sidebarOpen={sidebarOpen}
          onToggleSidebar={() => setSidebarOpen((o) => !o)}
        />
        <div className="flex-1 px-4 py-6 sm:px-8 sm:py-8">{children}</div>
      </main>
      <MobileNav active={active} />
    </div>
  );
}

function TopBar({
  active,
  identity,
  showToggle,
  sidebarOpen,
  onToggleSidebar,
}: {
  active?: string;
  identity: { label: string; isGuest: boolean };
  showToggle: boolean;
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
}) {
  return (
    <header className="flex items-center justify-between border-b border-[color:var(--purch-line)] bg-[color:var(--purch-paper)] px-7 py-3.5">
      <div className="flex items-center gap-3">
        {showToggle && (
          <button
            onClick={onToggleSidebar}
            aria-label={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
            className="flex items-center justify-center h-8 w-8 rounded-md text-[color:var(--purch-taupe)] hover:text-[color:var(--purch-rust)] hover:bg-[color:var(--purch-bg)] transition-colors"
          >
            {sidebarOpen ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}
          </button>
        )}
        <Link href="/chat" aria-label="Go to Chat" className="flex items-center gap-3">
          <Brand size="sm" mark showBeta={false} />
        </Link>
        <nav className="hidden md:flex items-center gap-1 ml-3">
          {NAV.map((n) => {
            const isActive = active === n.href;
            const Icon = n.icon;
            return (
              <Link
                key={n.href}
                href={n.href}
                className={
                  "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-[13.5px] transition-colors " +
                  (isActive
                    ? "bg-[#CDBFA6] font-semibold text-[color:var(--purch-ink)]"
                    : "text-[color:var(--purch-taupe)] hover:text-[color:var(--purch-ink)] hover:bg-[color:var(--purch-bg)]")
                }
              >
                <Icon size={15} />
                {n.label}
              </Link>
            );
          })}
        </nav>
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

// --------------------------------------------------------------------------- //
// Global toast notification — a SINGLE live alert that slides in from the
// right (like a phone notification), sits at top-right, and auto-dismisses
// after 5s. Only one is shown at a time so it never stacks or fills the page.
// Mount <ToastProvider> once in layout.tsx; call useToast().push(msg).
// --------------------------------------------------------------------------- //
type ToastKind = "info" | "success" | "warning" | "danger";
interface ToastItem {
  id: number;
  kind: ToastKind;
  message: string;
}

const ToastCtx = createContext<{ push: (message: string, kind?: ToastKind) => void } | null>(null);

export function useToast() {
  const ctx = useContext(ToastCtx);
  if (!ctx) {
    return { push: (_m: string, _k?: ToastKind) => {} };
  }
  return ctx;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toast, setToast] = useState<ToastItem | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const push = useCallback((message: string, kind: ToastKind = "info") => {
    if (timer.current) clearTimeout(timer.current);
    setToast({ id: Date.now() + Math.random(), kind, message });
    timer.current = setTimeout(() => setToast(null), 5000);
  }, []);

  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);

  // Memoize the context value so consumers' effects don't re-run every render
  // (an unstable object here caused an infinite setState loop → "Maximum
  // update depth exceeded" and broke the 5s auto-dismiss).
  const value = useMemo(() => ({ push }), [push]);

  return (
    <ToastCtx.Provider value={value}>
      {children}
      <div className="fixed top-3 right-3 z-[100] pointer-events-none">
        {toast && (
          <div
            key={toast.id}
            className="purch-toast pointer-events-auto max-w-[88vw] sm:max-w-[360px] w-full rounded-lg px-4 py-3 text-[13.5px] font-medium shadow-lg"
            style={{
              background:
                toast.kind === "danger"
                  ? "var(--purch-rust)"
                  : toast.kind === "warning"
                  ? "#E8B33D"
                  : toast.kind === "success"
                  ? "var(--purch-pine)"
                  : "var(--purch-ink)",
              color: toast.kind === "warning" ? "var(--purch-ink)" : "var(--purch-paper)",
            }}
            role="status"
          >
            {toast.message}
          </div>
        )}
      </div>
    </ToastCtx.Provider>
  );
}


