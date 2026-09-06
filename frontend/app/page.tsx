"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Brand } from "@/lib/ui";
import { PerforatedEdge, ReceiptHeader } from "@/lib/receipt";
import { createClient } from "@/lib/supabase/client";
import { isGuest } from "@/lib/guest";

/* ── CountUp component for animated numbers ── */
function CountUp({ target, prefix = "", suffix = "", duration = 800 }: { target: number; prefix?: string; suffix?: string; duration?: number }) {
  const ref = useRef<HTMLSpanElement>(null);
  const [value, setValue] = useState(0);
  const started = useRef(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !started.current) {
          started.current = true;
          const start = performance.now();
          const animate = (now: number) => {
            const elapsed = now - start;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            setValue(Math.floor(target * eased));
            if (progress < 1) requestAnimationFrame(animate);
            else setValue(target);
          };
          requestAnimationFrame(animate);
        }
      },
      { threshold: 0.5 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [target, duration]);

  return <span ref={ref}>{prefix}{value.toLocaleString()}{suffix}</span>;
}

/* ── Visitors Design Tokens (landing page only) ── */
const V = {
  carbon: "#181925",
  paper: "#ffffff",
  linen: "#fafafa",
  mist: "#f5f5f5",
  fog: "#e8e8e8",
  ash: "#999999",
  graphite: "#666666",
  lavender: "#7c6edc",
  iris: "#8575e8",
  mint: "#33c758",
  mintWash: "#def6e4",
  amber: "#ffa600",
  sky: "#2c78fc",
  magenta: "#d6409f",
  ember: "#ff3e00",
};

const NAV_LINKS = [
  { label: "Features", href: "#features" },
  { label: "How it works", href: "#how-it-works" },
  { label: "Contact", href: "#footer" },
];

const FEATURES = [
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
        <path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        <path d="M9.09 9C9.3251 8.33167 9.78915 7.76811 10.4 7.40913C11.011 7.05016 11.6297 6.93872 12.2272 7.08871C12.8247 7.2387 13.3213 7.63977 13.5686 8.1898L13.9111 9.19M13.9111 9.19L15.5 11.32M13.9111 9.19L12.5 12L11 10.5M13.9111 9.19L12.1628 11.7665C12.0811 11.9015 12.0383 12.0435 12.0357 12.1884C12.0331 12.3333 12.0707 12.4771 12.1464 12.6143C12.2221 12.7514 12.3345 12.8797 12.4781 12.9938L14.5 14.5M9.5 14.5C10.0435 13.8965 10.5817 13.2398 11.0036 12.5521C11.4255 11.8644 11.7348 11.1555 11.94 10.4441" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    ),
    title: "Chat-first logging",
    desc: "Just type or talk. No forms, no spreadsheets, no friction.",
  },
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
        <path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        <path d="M12 8V12M12 16H12.01M17 12C17 14.2091 15.2091 16 13 16C14.4207 16 15.6787 15.2874 16.3246 14.1832C16.9706 13.079 17 11.7148 16.6268 10.6165C16.2536 9.51832 15.4415 8.63231 14.3766 8.14567C13.3116 7.65903 12.0688 7.60508 11.0003 8.00507C9.93182 8.40506 9.05513 9.25419 8.58551 10.3177C8.11589 11.3813 8.09351 12.5917 8.52112 13.6167" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    ),
    title: "Multiple personas",
    desc: "Pick a tone — Neutral, Bestie, Sarcastic, Coach. Your money, your voice.",
  },
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
        <path d="M3 12L5 10V8C5 5.79086 6.79086 4 9 4C10.64 4 12.0099 4.99434 12.6993 6.5C13.2756 7.77952 14.1995 8.78857 15.3932 9.42067C16.5871 10.0528 17.9337 10.2616 19 10C20.6569 9.63826 22 8.00735 22 6.18182C22 4.73805 20.9842 3.51881 19.6111 3.05506" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        <path d="M8 14C4.68629 14 2 16.6863 2 20C2 21.1046 2.89543 22 4 22H14C15.1046 22 16 21.1046 16 20C16 19.1139 15.4508 18.304 14.6955 17.8234C13.5944 17.1643 12.2498 16.8234 10.9235 16.8234" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    ),
    title: "Real insights",
    desc: "See where your money actually goes, in language you understand.",
  },
];

const STEPS = [
  { num: "1", title: "Sign up & pick your persona", desc: "Choose from Neutral, Bestie, Sarcastic, Coach — or create your own." },
  { num: "2", title: "Start chatting your expenses", desc: "Type or speak like you text a friend. No forms, no frills." },
  { num: "3", title: "Watch your budget make sense", desc: "Get daily insights, spending trends, and category breakdowns." },
];

/* ── Pill button styles ── */
const pillBtn: React.CSSProperties = {
  borderRadius: 9999,
  fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif",
  fontWeight: 500,
  fontSize: 14,
  letterSpacing: "-0.023em",
  padding: "10px 20px",
  border: "none",
  cursor: "pointer",
  transition: "opacity 0.15s, transform 0.15s",
};
const primaryBtn: React.CSSProperties = {
  ...pillBtn,
  background: V.lavender,
  color: "#fff",
  boxShadow: "rgba(0,0,0,0.08) 0px 1px 1px 1px, rgba(0,0,0,0.06) 0px 0px 0px 0.5px",
};
const ghostBtn: React.CSSProperties = {
  ...pillBtn,
  background: "transparent",
  color: V.graphite,
  padding: "10px 20px",
};

function Navbar() {
  return (
    <header
      style={{
        position: "fixed", top: 16, left: 0, right: 0, zIndex: 30,
        display: "flex", justifyContent: "center",
        padding: "0 24px",
      }}
    >
      <nav style={{
        display: "flex", alignItems: "center", gap: 4,
        background: "#1a1a2e", borderRadius: 9999,
        padding: "8px 8px 8px 16px",
        boxShadow: "0 4px 24px rgba(0,0,0,0.2)",
      }}>
        {/* Logo */}
        <Link href="/" style={{ display: "flex", alignItems: "center", gap: 6, textDecoration: "none", marginRight: 8 }}>
          <div style={{ width: 28, height: 28, borderRadius: "50%", background: "#fff", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <span style={{ fontSize: 14, fontWeight: 700, color: "#1a1a2e", fontFamily: "'Playfair Display', Georgia, serif" }}>P</span>
          </div>
        </Link>

        {/* Nav links — hidden on mobile */}
        <div className="hidden sm:flex items-center gap-1">
          {NAV_LINKS.map((link) => (
            <Link key={link.label} href={link.href} style={{ fontSize: 13, fontWeight: 500, color: "rgba(255,255,255,0.7)", padding: "6px 12px", borderRadius: 9999, letterSpacing: "-0.023em", textDecoration: "none", transition: "color 0.15s" }}>
              {link.label}
            </Link>
          ))}
        </div>

        {/* Login — visible on mobile */}
        <Link href="/auth/login" className="inline-flex" style={{ fontSize: 13, fontWeight: 500, color: "rgba(255,255,255,0.7)", padding: "6px 12px", borderRadius: 9999, letterSpacing: "-0.023em", textDecoration: "none", transition: "color 0.15s" }}>
          Login
        </Link>

        {/* Register button */}
        <Link href="/auth/register" style={{ fontSize: 13, fontWeight: 600, color: "#fff", background: "#7C6EDC", padding: "8px 20px", borderRadius: 9999, letterSpacing: "-0.023em", textDecoration: "none", marginLeft: 4, transition: "opacity 0.15s" }}>
          Register
        </Link>
      </nav>
    </header>
  );
}

export default function LandingPage() {
  const router = useRouter();
  const [isAuthed, setIsAuthed] = useState(false);
  const [heroText, setHeroText] = useState("");
  const [heroPhase, setHeroPhase] = useState(0);
  const heroLines = ["Talk to your money.", "Track every peso", "without lifting a finger."];
  const fullText = heroLines.join("\n");

  // Typewriter for hero headline
  useEffect(() => {
    let idx = 0;
    const timer = setInterval(() => {
      idx++;
      setHeroText(fullText.slice(0, idx));
      if (idx >= fullText.length) clearInterval(timer);
    }, 35);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getSession().then(({ data }) => {
      if (data.session && !isGuest()) {
        setIsAuthed(true);
        router.replace("/chat");
      }
    });

    // Bidirectional scroll reveal
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) entry.target.classList.add("is-visible");
          else entry.target.classList.remove("is-visible");
        });
      },
      { threshold: 0.15 }
    );
    const timer = setTimeout(() => {
      document.querySelectorAll(".purch-reveal").forEach((el) => observer.observe(el));
    }, 50);
    return () => { observer.disconnect(); clearTimeout(timer); };
  }, [router]);

  if (isAuthed) return null;

  // Split hero text into lines for rendering
  const renderedLines = heroText.split("\n");

  return (
    <main style={{ fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif", background: V.paper, color: V.carbon }}>
      <Navbar />

      {/* ── Hero ── */}
      <section className="purch-reveal" style={{ paddingTop: 120, paddingBottom: 64 }}>
        <div style={{ maxWidth: 1200, margin: "0 auto", padding: "0 24px", textAlign: "center" }}>
          {/* Announcement chip */}
          <div style={{ display: "inline-flex", alignItems: "center", gap: 6, background: V.paper, border: `1px solid ${V.fog}`, borderRadius: 9999, padding: "6px 14px", marginBottom: 32, fontSize: 14, fontWeight: 500, color: V.carbon, letterSpacing: "-0.023em", boxShadow: "rgba(0,0,0,0.04) 0px 1px 2px" }}>
            <span style={{ color: V.sky, fontWeight: 600, fontSize: 12 }}>NEW</span>
            Built for Filipino freelancers, students, and households
            <ArrowRight size={14} style={{ color: V.carbon }} />
          </div>

          <h1 style={{ fontSize: "clamp(2.5rem,6vw,60px)", lineHeight: 1.13, letterSpacing: "-3px", fontWeight: 600, color: V.carbon, margin: "0 0 24px", padding: 0, minHeight: "3.4em" }}>
            {renderedLines.map((line, i) => (
              <span key={i}>
                {i === 2 ? <span style={{ color: V.lavender }}>{line}</span> : line}
                {i < renderedLines.length - 1 && <br />}
              </span>
            ))}
            {heroText.length < fullText.length && <span style={{ display: "inline-block", width: 3, height: "0.85em", background: V.lavender, marginLeft: 2, verticalAlign: "baseline", animation: "blink 0.6s step-end infinite" }} />}
          </h1>

          <p style={{ fontSize: 16, lineHeight: 1.5, letterSpacing: "-0.32px", color: V.graphite, maxWidth: 480, margin: "0 auto 40px" }}>
            Purch turns budgeting into a conversation — log expenses, get
            insights, and stay on top of your peso in whatever tone fits your mood.
          </p>

          <div style={{ display: "flex", flexDirection: "row", justifyContent: "center", gap: 12, flexWrap: "wrap", marginBottom: 48 }}>
            <Link href="/chat" style={{ ...primaryBtn, display: "inline-flex", alignItems: "center", gap: 6, textDecoration: "none" }}>
              Start Free <ArrowRight size={15} />
            </Link>
            <button style={ghostBtn}>
              See Demo
            </button>
          </div>

          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 32, opacity: 0.4, fontSize: 12, fontWeight: 500, color: V.ash, letterSpacing: "0.05em", textTransform: "uppercase" }}>
            <span>Freelancers</span>
            <span style={{ width: 4, height: 4, borderRadius: "50%", background: V.fog }} />
            <span>Students</span>
            <span style={{ width: 4, height: 4, borderRadius: "50%", background: V.fog }} />
            <span>Households</span>
          </div>
        </div>
      </section>

      {/* ── Gradient band + browser-framed dashboard mockup ── */}
      <section className="purch-reveal" style={{ background: "linear-gradient(135deg, #2c78fc, #7c6edc)", padding: "64px 24px" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          {/* Mac browser frame */}
          <div style={{
            background: V.paper, borderRadius: 12, overflow: "hidden",
            boxShadow: "0 8px 32px rgba(0,0,0,0.18), 0 2px 8px rgba(0,0,0,0.08)",
          }}>
            {/* Title bar */}
            <div style={{ background: V.linen, borderBottom: `1px solid ${V.fog}`, padding: "10px 16px", display: "flex", alignItems: "center", gap: 12 }}>
              {/* Traffic lights */}
              <div style={{ display: "flex", gap: 6 }}>
                <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#FF5F57" }} />
                <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#FEBC2E" }} />
                <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#28C840" }} />
              </div>
              {/* Navigation arrows */}
              <div style={{ display: "flex", gap: 8, marginLeft: 8 }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={V.ash} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={V.fog} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
              </div>
              {/* Search bar */}
              <div style={{ flex: 1, background: V.paper, border: `1px solid ${V.fog}`, borderRadius: 8, padding: "6px 14px", display: "flex", alignItems: "center", gap: 8 }}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke={V.ash} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                <span style={{ fontSize: 12, color: V.graphite, fontFamily: "'JetBrains Mono', monospace" }}>the-purch.vercel.app/chat</span>
              </div>
            </div>

            {/* Dashboard content */}
            <div style={{ display: "flex", flexWrap: "wrap", minHeight: 380 }}>
            {/* Left column — Budget Status + Last 7 Days + Transactions */}
            <div style={{ flex: "1 1 620px", padding: 24, display: "flex", flexDirection: "column", gap: 20, borderRight: `1px solid ${V.fog}` }}>

              {/* Top row — Budget Status + Last 7 Days */}
              <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>

                {/* Budget Status */}
                <div style={{ flex: "1 1 220px", border: `1px solid ${V.fog}`, borderRadius: 12, padding: 20 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: V.carbon, marginBottom: 16 }}>Budget Status</div>
                  {[
                    { cat: "Food & Dining", spent: 2800, limit: 3500, color: V.lavender },
                    { cat: "Transport", spent: 650, limit: 1000, color: V.sky },
                    { cat: "Shopping", spent: 1200, limit: 1500, color: V.magenta },
                  ].map((b) => {
                    const pct = Math.round((b.spent / b.limit) * 100);
                    return (
                      <div key={b.cat} style={{ marginBottom: 14 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                          <span style={{ fontSize: 12, color: V.graphite }}>{b.cat}</span>
                          <span style={{ fontSize: 12, fontFamily: "'JetBrains Mono', monospace", color: V.carbon }}><CountUp target={b.spent} prefix="₱" /><span style={{ color: V.ash }}> / <CountUp target={b.limit} prefix="₱" /></span></span>
                        </div>
                        <div style={{ height: 6, borderRadius: 3, background: V.fog, overflow: "hidden" }}>
                          <div style={{ height: "100%", width: `${pct}%`, borderRadius: 3, background: b.color, transition: "width 0.3s" }} />
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Last 7 Days */}
                <div style={{ flex: "1 1 240px", border: `1px solid ${V.fog}`, borderRadius: 12, padding: 20 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: V.carbon, marginBottom: 8 }}>Last 7 Days</div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
                    <div>
                      <div style={{ fontSize: 11, color: V.ash }}>This Week</div>
                      <div style={{ fontSize: 20, fontWeight: 600, fontFamily: "'JetBrains Mono', monospace", color: V.carbon }}><CountUp target={2450} prefix="₱" /></div>
                    </div>
                    <div>
                      <div style={{ fontSize: 11, color: V.ash }}>Transactions</div>
                      <div style={{ fontSize: 20, fontWeight: 600, fontFamily: "'JetBrains Mono', monospace", color: V.carbon }}><CountUp target={47} /></div>
                    </div>
                  </div>
                  {/* Mini bar chart */}
                  <div style={{ display: "flex", alignItems: "flex-end", gap: 6, height: 60 }}>
                    {[180, 320, 90, 450, 280, 520, 150].map((h, i) => (
                      <div key={i} style={{ flex: 1, height: `${(h / 520) * 100}%`, borderRadius: 3, background: i === 5 ? V.lavender : V.fog }} />
                    ))}
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6 }}>
                    {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d) => (
                      <span key={d} style={{ flex: 1, textAlign: "center", fontSize: 9, color: V.ash }}>{d}</span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Transaction History */}
              <div style={{ border: `1px solid ${V.fog}`, borderRadius: 12, overflow: "hidden" }}>
                <div style={{ padding: "12px 16px", borderBottom: `1px solid ${V.fog}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 13, fontWeight: 600, color: V.carbon }}>Transaction History</span>
                  <div style={{ display: "flex", gap: 8 }}>
                    <span style={{ fontSize: 11, padding: "3px 10px", borderRadius: 9999, background: V.lavender, color: "#fff", fontWeight: 500 }}>Today</span>
                    <span style={{ fontSize: 11, padding: "3px 10px", borderRadius: 9999, background: V.mist, color: V.graphite, fontWeight: 500 }}>This Week</span>
                  </div>
                </div>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: `1px solid ${V.fog}` }}>
                      <th style={{ textAlign: "left", padding: "10px 16px", fontWeight: 500, color: V.ash, fontSize: 11 }}>Item</th>
                      <th style={{ textAlign: "left", padding: "10px 16px", fontWeight: 500, color: V.ash, fontSize: 11 }}>Category</th>
                      <th style={{ textAlign: "left", padding: "10px 16px", fontWeight: 500, color: V.ash, fontSize: 11 }}>Wallet</th>
                      <th style={{ textAlign: "right", padding: "10px 16px", fontWeight: 500, color: V.ash, fontSize: 11 }}>Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      { item: "Milk Tea", cat: "Food & Dining", catColor: V.lavender, wallet: "GCash", amount: "-₱85" },
                      { item: "Jeepney", cat: "Transport", catColor: V.sky, wallet: "Cash", amount: "-₱15" },
                      { item: "Lunch", cat: "Food & Dining", catColor: V.lavender, wallet: "GCash", amount: "-₱120" },
                      { item: "Grab", cat: "Transport", catColor: V.sky, wallet: "GCash", amount: "-₱250" },
                      { item: "Shopee", cat: "Shopping", catColor: V.magenta, wallet: "BPI", amount: "-₱450" },
                    ].map((t, i) => (
                      <tr key={i} style={{ borderBottom: `1px solid ${V.fog}` }}>
                        <td style={{ padding: "10px 16px", color: V.carbon, fontWeight: 500 }}>{t.item}</td>
                        <td style={{ padding: "10px 16px" }}>
                          <span style={{ display: "inline-block", padding: "2px 8px", borderRadius: 9999, fontSize: 11, fontWeight: 500, background: `${t.catColor}18`, color: t.catColor }}>{t.cat}</span>
                        </td>
                        <td style={{ padding: "10px 16px", fontSize: 12, color: V.graphite }}>{t.wallet}</td>
                        <td style={{ padding: "10px 16px", textAlign: "right", fontFamily: "'JetBrains Mono', monospace", fontWeight: 500, color: V.carbon }}>{t.amount}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Right column — Wallets + Assistant chat */}
            <div style={{ flex: "1 1 340px", display: "flex", flexDirection: "column", background: V.linen, gap: 16, padding: 16 }}>

              {/* Wallet card */}
              <div style={{ background: V.paper, border: `1px solid ${V.fog}`, borderRadius: 12, padding: 16 }}>
                <div style={{ fontSize: 11, fontWeight: 500, color: V.ash, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 12 }}>Wallets</div>
                {/* Stacked wallet cards */}
                <div style={{ position: "relative", height: 110 }}>
                  {[
                    { name: "Cash", balance: "₱1,200", color: "#7A1F2B", offset: 0 },
                    { name: "BPI Savings", balance: "₱12,350", color: "#1A1F36", offset: 1 },
                    { name: "GCash", balance: "₱4,520", color: "#0D73EC", offset: 2 },
                  ].map((w, i) => (
                    <div key={w.name} style={{
                      position: "absolute", left: 0, right: 0,
                      top: w.offset * 30,
                      height: 40,
                      background: w.color, color: "#fff",
                      borderRadius: 10,
                      display: "flex", alignItems: "center", justifyContent: "space-between",
                      padding: "0 14px",
                      boxShadow: i === 2 ? "0 2px 8px rgba(0,0,0,0.15)" : "0 1px 3px rgba(0,0,0,0.08)",
                      zIndex: i,
                    }}>
                      <span style={{ fontSize: 11, fontWeight: 500 }}>{w.name}</span>
                      <span style={{ fontSize: 13, fontWeight: 600, fontFamily: "'JetBrains Mono', monospace" }}>{w.balance}</span>
                    </div>
                  ))}
                </div>
                {/* Summary card with concave notch */}
                <div style={{ marginTop: -8 }}>
                  <svg width="100%" height="12" viewBox="0 0 300 12" preserveAspectRatio="none" style={{ display: "block", marginTop: -1 }}>
                    <path d="M0,0 L120,0 C130,0 135,3 140,6 C145,9 150,12 150,12 C150,12 155,9 160,6 C165,3 170,0 180,0 L300,0 L300,12 L0,12 Z" fill="#fff" />
                  </svg>
                  <div style={{
                    background: "#fff", borderRadius: "0 0 10px 10px", padding: "10px 14px",
                    display: "flex", justifyContent: "space-between", alignItems: "center",
                    marginTop: -2,
                    boxShadow: "0 2px 8px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04)",
                  }}>
                    <div>
                      <div style={{ fontSize: 11, color: V.ash }}>3 Wallets</div>
                      <div style={{ fontSize: 10, color: V.graphite }}>Wallet Balance</div>
                    </div>
                    <div style={{ fontSize: 18, fontWeight: 700, fontFamily: "'JetBrains Mono', monospace", color: V.carbon }}><CountUp target={18070} prefix="₱" /></div>
                  </div>
                </div>
              </div>

              {/* Assistant chat card */}
              <div style={{ background: V.paper, border: `1px solid ${V.fog}`, borderRadius: 12, overflow: "hidden", flex: 1, display: "flex", flexDirection: "column" }}>
                <div style={{ padding: "12px 16px", borderBottom: `1px solid ${V.fog}`, display: "flex", alignItems: "center", gap: 10 }}>
                  <div style={{ width: 28, height: 28, borderRadius: "50%", background: "linear-gradient(135deg, #7c6edc, #8575e8)", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: 13, fontWeight: 600 }}>P</div>
                  <span style={{ fontSize: 14, fontWeight: 500, color: V.carbon }}>Assistant</span>
                </div>

                <div style={{ padding: "16px 16px 20px", display: "flex", flexDirection: "column", gap: 10, flex: 1 }}>
                  <div style={{ display: "flex", justifyContent: "flex-end" }}>
                    <div style={{ maxWidth: "78%", background: "linear-gradient(135deg, #7c6edc, #8575e8)", color: "#fff", padding: "10px 16px", borderRadius: 12, fontSize: 13, lineHeight: 1.5 }}>milk tea 85 gcash</div>
                  </div>
                  <div style={{ display: "flex", justifyContent: "flex-start" }}>
                    <div style={{ maxWidth: "78%", background: V.linen, color: V.carbon, padding: "10px 16px", borderRadius: 12, fontSize: 13, lineHeight: 1.5 }}>Logged! <strong>Milk Tea</strong> — <span style={{ fontFamily: "'JetBrains Mono', monospace", fontWeight: 500 }}>₱85.00</span> under Food &amp; Dining.</div>
                  </div>
                  <div style={{ display: "flex", justifyContent: "flex-end" }}>
                    <div style={{ maxWidth: "78%", background: "linear-gradient(135deg, #7c6edc, #8575e8)", color: "#fff", padding: "10px 16px", borderRadius: 12, fontSize: 13, lineHeight: 1.5 }}>how much did i spend this week?</div>
                  </div>
                  <div style={{ display: "flex", justifyContent: "flex-start" }}>
                    <div style={{ maxWidth: "78%", background: V.linen, color: V.carbon, padding: "10px 16px", borderRadius: 12, fontSize: 13, lineHeight: 1.5 }}>You&apos;ve spent <span style={{ fontFamily: "'JetBrains Mono', monospace", fontWeight: 500 }}>₱2,450</span> this week — mostly on <strong>Food</strong> (₱1,280).</div>
                  </div>
                  <div style={{ display: "flex", justifyContent: "flex-end" }}>
                    <div style={{ maxWidth: "78%", background: "linear-gradient(135deg, #7c6edc, #8575e8)", color: "#fff", padding: "10px 16px", borderRadius: 12, fontSize: 13, lineHeight: 1.5 }}>jeep 15 gcash</div>
                  </div>
                  <div style={{ display: "flex", justifyContent: "flex-start" }}>
                    <div style={{ maxWidth: "78%", background: V.linen, color: V.carbon, padding: "10px 16px", borderRadius: 12, fontSize: 13, lineHeight: 1.5 }}>Got it! <strong>Jeepney</strong> — <span style={{ fontFamily: "'JetBrains Mono', monospace", fontWeight: 500 }}>₱15.00</span> under Transport.</div>
                  </div>
                </div>

                <div style={{ padding: "12px 16px", borderTop: `1px solid ${V.fog}`, display: "flex", alignItems: "center", gap: 10 }}>
                  <div style={{ flex: 1, background: V.linen, border: `1px solid ${V.fog}`, borderRadius: 12, padding: "10px 14px", fontSize: 13, color: V.ash }}>Milk tea 85 Gcash…</div>
                  <div style={{ width: 32, height: 32, borderRadius: "50%", background: "linear-gradient(135deg, #7c6edc, #8575e8)", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 2L11 13"/><path d="M22 2L15 22L11 13L2 9L22 2Z"/></svg>
                  </div>
                </div>
              </div>
            </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section className="purch-reveal" style={{ background: V.paper, padding: "96px 24px" }} id="features">
        <div style={{ maxWidth: 1200, margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: 64 }}>
            <h2 style={{ fontSize: "clamp(1.5rem,4vw,36px)", lineHeight: 1.22, letterSpacing: "-0.61px", fontWeight: 600, color: V.carbon, margin: "0 0 16px" }}>
              Money management that actually fits how you talk.
            </h2>
            <p style={{ fontSize: 16, lineHeight: 1.5, color: V.graphite, maxWidth: 520, margin: "0 auto" }}>
              No spreadsheets, no categories to manage, no app to learn. Just chat like you would with a friend who keeps you honest.
            </p>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 32 }}>
            {FEATURES.map((f, i) => (
              <div key={f.title} className="purch-reveal" style={{ textAlign: "center", padding: "32px 0", transitionDelay: `${(i + 1) * 100}ms` }}>
                <div style={{ width: 40, height: 40, borderRadius: "50%", background: V.lavender, display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 16px", color: "#fff" }}>
                  {f.icon}
                </div>
                <h3 style={{ fontSize: 18, fontWeight: 500, color: V.carbon, letterSpacing: "-0.018em", margin: "0 0 8px" }}>{f.title}</h3>
                <p style={{ fontSize: 16, lineHeight: 1.5, color: V.graphite, letterSpacing: "-0.32px", margin: 0 }}>{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Steps ── */}
      <section className="purch-reveal" style={{ background: V.linen, padding: "96px 24px" }} id="how-it-works">
        <div style={{ maxWidth: 1200, margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: 64 }}>
            <h2 style={{ fontSize: "clamp(1.5rem,4vw,36px)", lineHeight: 1.22, letterSpacing: "-0.61px", fontWeight: 600, color: V.carbon, margin: "0 0 16px" }}>
              Get started in three quick steps.
            </h2>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 32, maxWidth: 1000, margin: "0 auto" }}>
            {STEPS.map((step, i) => (
              <div key={step.num} className="purch-reveal" style={{ padding: 32, borderRadius: 16, background: V.paper, border: `1px solid ${V.fog}`, transitionDelay: `${(i + 1) * 100}ms` }}>
                <div style={{ fontSize: 48, fontWeight: 600, color: V.fog, lineHeight: 1, marginBottom: 16 }}>{step.num}</div>
                <h3 style={{ fontSize: 18, fontWeight: 500, color: V.carbon, letterSpacing: "-0.018em", margin: "0 0 8px" }}>{step.title}</h3>
                <p style={{ fontSize: 16, lineHeight: 1.5, color: V.graphite, letterSpacing: "-0.32px", margin: 0 }}>{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA banner ── */}
      <section style={{ padding: "96px 24px", background: V.paper }} className="purch-reveal">
        <div style={{ maxWidth: 800, margin: "0 auto", textAlign: "center" }}>
          <h2 style={{ fontSize: "clamp(1.5rem,4vw,36px)", lineHeight: 1.22, letterSpacing: "-0.61px", fontWeight: 600, color: V.carbon, margin: "0 0 16px" }}>
            Ready to stop guessing with your money?
          </h2>
          <p style={{ fontSize: 16, lineHeight: 1.5, color: V.graphite, marginBottom: 32 }}>
            Start logging your expenses in seconds. No credit card needed.
          </p>
          <div style={{ display: "flex", justifyContent: "center", gap: 12, flexWrap: "wrap" }}>
            <Link href="/chat" style={{ ...primaryBtn, display: "inline-flex", alignItems: "center", gap: 6, textDecoration: "none" }}>
              Get Started Now <ArrowRight size={15} />
            </Link>
            <Link href="#features" style={{ ...ghostBtn, display: "inline-flex", alignItems: "center", gap: 6, textDecoration: "none" }}>
              Learn More <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer id="footer" style={{ background: V.linen, borderTop: `1px solid ${V.fog}`, padding: "64px 24px 32px" }}>
        <div style={{ maxWidth: 1200, margin: "0 auto" }}>
          <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", gap: 48, marginBottom: 48 }}>
            <div>
              <span style={{ fontFamily: "'Playfair Display', Georgia, serif", fontWeight: 600, fontStyle: "italic", fontSize: 22, background: "linear-gradient(135deg, #7c6edc, #8575e8)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", letterSpacing: "-0.02em" }}>purch</span>
              <p style={{ fontSize: 12, color: V.ash, marginTop: 8, maxWidth: 280 }}>Created by Aivann Herald Martinez. Built for Filipino money habits.</p>
              <div style={{ display: "flex", gap: 14, marginTop: 12 }}>
                <a href="https://github.com/vanzmhl" target="_blank" rel="noopener noreferrer" style={{ color: V.graphite }} aria-label="GitHub">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>
                </a>
                <a href="mailto:aivann.martinez@gmail.com" style={{ color: V.graphite }} aria-label="Email">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>
                </a>
                <a href="https://linkedin.com/in/aivannmartinez" target="_blank" rel="noopener noreferrer" style={{ color: V.graphite }} aria-label="LinkedIn">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.607H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
                </a>
                <a href="tel:+6391234567890" style={{ color: V.graphite }} aria-label="Phone">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
                </a>
              </div>
            </div>
            <div style={{ display: "flex", gap: 48 }}>
              <div>
                <h4 style={{ fontSize: 12, fontWeight: 500, color: V.ash, textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 12px" }}>Product</h4>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  <Link href="#features" style={{ fontSize: 14, color: V.graphite, textDecoration: "none" }}>Features</Link>
                  <Link href="#how-it-works" style={{ fontSize: 14, color: V.graphite, textDecoration: "none" }}>How it works</Link>
                </div>
              </div>
              <div>
                <h4 style={{ fontSize: 12, fontWeight: 500, color: V.ash, textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 12px" }}>Company</h4>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  <Link href="/about" style={{ fontSize: 14, color: V.graphite, textDecoration: "none" }}>About</Link>
                  <Link href="/contact" style={{ fontSize: 14, color: V.graphite, textDecoration: "none" }}>Contact</Link>
                </div>
              </div>
              <div>
                <h4 style={{ fontSize: 12, fontWeight: 500, color: V.ash, textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 12px" }}>Resources</h4>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  <Link href="/guides" style={{ fontSize: 14, color: V.graphite, textDecoration: "none" }}>Guides</Link>
                  <Link href="/faq" style={{ fontSize: 14, color: V.graphite, textDecoration: "none" }}>FAQ</Link>
                </div>
              </div>
            </div>
          </div>
          <div style={{ borderTop: `1px solid ${V.fog}`, paddingTop: 24 }}>
            <p style={{ fontSize: 12, color: V.ash, margin: 0 }}>© 2026 Purch. Built for Filipino money habits.</p>
          </div>
        </div>
      </footer>
    </main>
  );
}
