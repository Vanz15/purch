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
  "font-sans font-extrabold tracking-tight text-[color:var(--purch-ink)]";

export const primaryButton =
  "inline-flex items-center justify-center gap-2 rounded-full " +
  "bg-[color:var(--purch-accent)] hover:opacity-90 " +
  "text-white font-medium px-5 py-2.5 transition-opacity";

export const outlineButton =
  "inline-flex items-center justify-center gap-2 rounded-full " +
  "border border-[color:var(--purch-line)] bg-white " +
  "text-[color:var(--purch-ink)] hover:border-[color:var(--purch-accent)] " +
  "transition-colors font-medium px-5 py-2.5";

export const ghostButton =
  "inline-flex items-center justify-center gap-2 rounded-full " +
  "text-[color:var(--purch-muted-ink)] hover:text-[color:var(--purch-accent)] " +
  "transition-colors font-medium px-4 py-2.5";

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
  ink: "#1D1D1F",
  paper: "#EAEAEA",
  rust: "#0A84FF",   // NOTE: keeping the key name "rust" to avoid renaming every call site;
                      // the VALUE is now the new accent blue.
  pine: "#2FA88A",
  gold: "#FFB020",
  taupe: "#86868B",
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
          className="flex h-7 w-7 items-center justify-center rounded-lg font-sans font-bold text-[15px]"
          style={{ background: C.ink, color: C.gold }}
        >
          P
        </span>
      )}
      <span
        className={`${sizeCls} font-semibold`}
        style={{ fontFamily: "'Playfair Display', Georgia, serif", fontWeight: 600, fontStyle: "italic", letterSpacing: "-0.02em", color: "#171717" }}
      >
        purch
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
      style={{ borderColor: C.taupe, color: "var(--purch-muted-ink)" }}
    >
      {tone}
    </span>
  );
}

import { PanelLeftClose, PanelLeftOpen, LogOut } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { guestName, guestDetail, isGuest, clearGuest } from "@/lib/guest";

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
                ? "bg-[#D4E8FF] text-[color:var(--purch-ink)]"
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
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const [identity, setIdentity] = useState<{ label: string; isGuest: boolean; email: string; detail: string }>({
    label: "",
    isGuest: false,
    email: "",
    detail: "",
  });
  const initial = identity.label ? identity.label.charAt(0).toUpperCase() : "G";

  // Close menu on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    if (menuOpen) document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [menuOpen]);

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
        setIdentity({ label: name, isGuest: false, email: u.email || "", detail: u.email || name });
      } else if (isGuest()) {
        setIdentity({ label: guestName(), isGuest: true, email: "", detail: guestDetail() });
      } else {
        setIdentity({ label: "Guest", isGuest: true, email: "", detail: "Guest" });
      }
    });
  }, []);

  function signOut() {
    const supabase = createClient();
    supabase.auth.signOut().finally(() => {
      clearGuest();
      window.location.href = "/";
    });
  }

  return (
    <div className="min-h-screen bg-[color:var(--purch-bg)]">
      {/* Dark floating pill navbar */}
      <header
        style={{
          position: "fixed", top: 12, left: 0, right: 0, zIndex: 30,
          display: "flex", justifyContent: "center",
          padding: "0 12px",
        }}
      >
        <nav style={{
          display: "flex", alignItems: "center", gap: 4,
          background: "#1a1a2e", borderRadius: 9999,
          padding: "6px 6px 6px 12px",
          boxShadow: "0 4px 24px rgba(0,0,0,0.2)",
          flexShrink: 1,
        }}>
          {/* Logo */}
          <Link href="/chat" aria-label="Go to Chat" style={{ display: "flex", alignItems: "center", gap: 6, textDecoration: "none", marginRight: 8 }}>
            <div style={{ width: 28, height: 28, borderRadius: "50%", background: "#fff", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <span style={{ fontSize: 14, fontWeight: 700, color: "#7C6EDC", fontFamily: "'Playfair Display', Georgia, serif" }}>P</span>
            </div>
          </Link>

          {/* Nav links — icons only on small screens, icons+text on sm+ */}
          <div className="flex items-center gap-1">
          {NAV.map((n) => {
            const isActive = active === n.href;
            const Icon = n.icon;
            return (
              <Link
                key={n.href}
                href={n.href}
                style={{
                  fontSize: 13, fontWeight: 500,
                  color: isActive ? "#fff" : "rgba(255,255,255,0.7)",
                  padding: "5px 10px", borderRadius: 9999,
                  letterSpacing: "-0.023em", textDecoration: "none",
                  background: isActive ? "rgba(255,255,255,0.12)" : "transparent",
                  transition: "all 0.15s",
                  display: "flex", alignItems: "center", gap: 5,
                }}
              >
                <Icon size={15} />
                <span className="hidden sm:inline">{n.label}</span>
              </Link>
            );
          })}
          </div>

          {/* Profile button */}
          <div ref={menuRef} style={{ position: "relative" }}>
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className="purch-btn-primary"
              style={{
                display: "flex", alignItems: "center", gap: 8,
                padding: "6px 12px 6px 6px",
                borderRadius: 9999, border: "none", cursor: "pointer",
                fontSize: 13, fontWeight: 500, letterSpacing: "-0.023em",
                transition: "opacity 0.15s",
              }}
            >
              <div style={{ width: 26, height: 26, borderRadius: "50%", background: "rgba(255,255,255,0.25)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 600, flexShrink: 0 }}>
                {initial}
              </div>
              <span className="hidden sm:inline" style={{ maxWidth: 80, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{identity.label}</span>
            </button>

            {menuOpen && (
              <div style={{
                position: "absolute", top: "100%", right: 0, marginTop: 8,
                background: "#fff", borderRadius: 12, padding: "6px 0",
                boxShadow: "rgba(0,0,0,0.06) 0px 1px 3px 0px, rgba(0,0,0,0.06) 0px 8px 16px 0px",
                border: "1px solid #e8e8e8", minWidth: 160, zIndex: 50,
              }}>
                <div style={{ padding: "8px 16px", borderBottom: "1px solid #e8e8e8" }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: "#181925" }}>{identity.label}</div>
                  {identity.detail && <div style={{ fontSize: 11, color: "#999", marginTop: 2 }}>{identity.detail}</div>}
                </div>
                <button
                  onClick={signOut}
                  style={{
                    display: "block", width: "100%", textAlign: "left", padding: "8px 16px",
                    fontSize: 13, color: "#666", background: "none", border: "none", cursor: "pointer",
                  }}
                >
                  Sign out
                </button>
              </div>
            )}
          </div>
        </nav>
      </header>

      <main className="pt-24 px-4 pb-6 sm:px-8 sm:py-8">{children}</main>
      {/* MobileNav removed — using floating pill navbar instead */}
    </div>
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
                  ? "var(--purch-gold)"
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


