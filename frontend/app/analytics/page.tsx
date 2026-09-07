"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { ChevronLeft, ChevronRight, RefreshCw, Search, AlertTriangle } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { api, AnalyticsResponse } from "@/lib/api";
import { PageShell, eyebrow, outlineButton, useToast } from "@/lib/ui";
import { isGuest } from "@/lib/guest";

const MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"];

// Category → color mapping (matches landing page dashboard mockup)
const CATEGORY_COLORS: Record<string, { bg: string; text: string }> = {
  "Food & Dining": { bg: "#EDE9FE", text: "#7c6edc" },
  "Transport": { bg: "#DBEAFE", text: "#2563EB" },
  "Shopping": { bg: "#FCE7F3", text: "#DB2777" },
  "Entertainment": { bg: "#FEF3C7", text: "#D97706" },
  "Bills & Utilities": { bg: "#D1FAE5", text: "#059669" },
  "Health": { bg: "#FEE2E2", text: "#DC2626" },
  "Education": { bg: "#E0E7FF", text: "#4F46E5" },
  "Groceries": { bg: "#ECFCCB", text: "#65A30D" },
  "Savings": { bg: "#CCFBF1", text: "#0D9488" },
  "Other": { bg: "#F3F4F6", text: "#6B7280" },
};

function getCategoryColors(category: string) {
  return CATEGORY_COLORS[category] || CATEGORY_COLORS["Other"];
}

// Counting animation hook
function useCountUp(target: number, duration: number = 800) {
  const [count, setCount] = useState(0);
  const frameRef = useRef<number | null>(null);
  const startTimeRef = useRef<number | null>(null);

  useEffect(() => {
    startTimeRef.current = null;
    const animate = (timestamp: number) => {
      if (!startTimeRef.current) startTimeRef.current = timestamp;
      const elapsed = timestamp - startTimeRef.current;
      const progress = Math.min(elapsed / duration, 1);
      // Ease-out cubic for smooth deceleration
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(Math.floor(target * eased));
      if (progress < 1) {
        frameRef.current = requestAnimationFrame(animate);
      } else {
        setCount(target);
      }
    };
    frameRef.current = requestAnimationFrame(animate);
    return () => { if (frameRef.current) cancelAnimationFrame(frameRef.current); };
  }, [target, duration]);

  return count;
}

// Typewriter animation hook
function useTypewriter(text: string, speed: number = 40) {
  const [displayed, setDisplayed] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    setDisplayed("");
    setDone(false);
    if (!text) return;
    let idx = 0;
    const interval = setInterval(() => {
      idx++;
      setDisplayed(text.slice(0, idx));
      if (idx >= text.length) {
        clearInterval(interval);
        setDone(true);
      }
    }, speed);
    return () => clearInterval(interval);
  }, [text, speed]);

  return { displayed, done };
}

// Scroll-triggered fade-in wrapper — triggers on mobile/tablet (sm screens), instant on desktop
function FadeInSection({ children, className = "", delay = 0, style: extraStyle }: { children: React.ReactNode; className?: string; delay?: number; style?: React.CSSProperties }) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const isMobile = window.matchMedia("(max-width: 639px)").matches;
    if (!isMobile) {
      setVisible(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.15 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={className}
      style={{
        ...extraStyle,
        opacity: visible ? 1 : 0,
        transform: visible ? "translateY(0)" : "translateY(24px)",
        transition: `opacity 500ms ease, transform 500ms ease ${delay}ms`,
      }}
    >
      {children}
    </div>
  );
}

// Animated KPI component with counting + typewriter effect
function KpiCard({ label, value, note, color, isNumber = false, prefix = "" }: {
  label: string;
  value: React.ReactNode | number;
  note: string;
  color?: string;
  isNumber?: boolean;
  prefix?: string;
}) {
  const numericValue = isNumber ? (typeof value === "number" ? value : 0) : 0;
  const displayValue = useCountUp(numericValue);
  const noteTypewriter = useTypewriter(note, 30);

  return (
    <div className="rounded-2xl p-5" style={{ background: "var(--purch-paper)", boxShadow: "var(--purch-shadow-sm)" }}>
      <div className={eyebrow} style={{ fontSize: 11 }}>{label}</div>
      <div className="font-sans font-semibold text-[26px] mt-2 mb-1" style={{ color: color || "var(--purch-ink)" }}>
        {isNumber ? `${prefix}${displayValue.toLocaleString()}` : value}
      </div>
      <div className="text-[11.5px] text-[color:var(--purch-muted-ink)]" style={{ minHeight: "1.2em" }}>
        {noteTypewriter.displayed}
        {!noteTypewriter.done && <span className="inline-block w-[1px] h-[11px] bg-[color:var(--purch-muted-ink)] animate-pulse ml-[1px]" />}
      </div>
    </div>
  );
}

// Line chart component for spending trend
function SpendingLineChart({ trend, peak, monthLabel }: { trend: { day: string; total: number }[]; peak: number; monthLabel: string }) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [points, setPoints] = useState<{ x: number; y: number; total: number }[]>([]);
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  useEffect(() => {
    if (!trend.length) return;

    const padding = { top: 24, right: 40, bottom: 20, left: 40 };
    const width = 300;
    const height = 60;

    const newPoints = trend.map((point, i) => {
    const x = (i / (trend.length - 1)) * (width - padding.left - padding.right) + padding.left;
    const ratio = peak > 0 ? point.total / peak : 0;
    const y = height - padding.bottom - (ratio * (height - padding.top - padding.bottom));
    return { x, y, total: point.total };
    });
    setPoints(newPoints);
  }, [trend, peak]);

  if (!trend.length) {
    return (
      <p className="text-sm text-[color:var(--purch-muted-ink)] italic py-6 text-center m-0">
        No activity this month — log a purchase to see the trend.
      </p>
    );
  }

  const svgHeight = 60;
  const svgWidth = 300;

  // Create smooth path
  const pathData = points.length > 1
    ? `M ${points.map(p => `${p.x},${p.y}`).join(" L ")}`
    : "";

  // Area fill path (line + bottom)
  const areaPath = pathData
    ? `${pathData} L ${points[points.length - 1].x},${svgHeight - 16} L ${points[0].x},${svgHeight - 16} Z`
    : "";

  return (
    <div className="w-full">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${svgWidth} ${svgHeight}`}
        className="w-full h-auto"
        preserveAspectRatio="none"
      >
        <defs>
          <linearGradient id="lineGradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="var(--purch-accent)" stopOpacity="0.3" />
            <stop offset="100%" stopColor="var(--purch-accent)" stopOpacity="0.05" />
          </linearGradient>
          <linearGradient id="strokeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="var(--purch-accent)" stopOpacity="0.5" />
            <stop offset="100%" stopColor="var(--purch-accent)" stopOpacity="1" />
          </linearGradient>
        </defs>

        {/* Area fill */}
        {areaPath && (
          <path
            d={areaPath}
            fill="url(#lineGradient)"
          />
        )}

        {/* Line */}
        {pathData && (
          <path
            d={pathData}
            fill="none"
            stroke="url(#strokeGradient)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        )}

        {/* Tick marks + data points + hover zones */}
        {points.map((point, i) => (
          <g key={i}>
            {/* Tick mark below node */}
            <line
              x1={point.x}
              y1={point.y + 6}
              x2={point.x}
              y2={svgHeight - 16}
              stroke="var(--purch-line)"
              strokeWidth="1"
            />
            {/* Invisible hover zone */}
            <rect
              x={point.x - 15}
              y={0}
              width={30}
              height={svgHeight}
              fill="transparent"
              onMouseEnter={() => setHoverIdx(i)}
              onMouseLeave={() => setHoverIdx(null)}
              style={{ cursor: "pointer" }}
            />
            {/* Data point */}
            <circle
              cx={point.x}
              cy={point.y}
              r={hoverIdx === i ? 5 : 3}
              fill="var(--purch-bg)"
              stroke="var(--purch-accent)"
              strokeWidth="2"
              style={{ transition: "r 0.15s ease" }}
            />
            {/* Tooltip */}
            {hoverIdx === i && (
              <g>
                <rect
                  x={point.x - 22}
                  y={point.y - 22}
                  width={44}
                  height={16}
                  rx={4}
                  fill="white"
                  stroke="var(--purch-line)"
                  strokeWidth="1"
                  filter="drop-shadow(0 1px 3px rgba(0,0,0,0.1))"
                />
                <text
                  x={point.x}
                  y={point.y - 11}
                  textAnchor="middle"
                  fill="var(--purch-ink)"
                  fontSize="9"
                  fontFamily="var(--font-fragment-mono)"
                >
                  ₱{point.total.toLocaleString()}
                </text>
              </g>
            )}
          </g>
        ))}
      </svg>

      {/* X-axis labels — first and last only */}
      <div className="flex justify-between text-[11px] text-[color:var(--purch-muted-ink)] mt-2 px-0">
        <span>{monthLabel} 1</span>
        <span>{monthLabel} {trend.length}</span>
      </div>
    </div>
  );
}

export default function AnalyticsPage() {
  const now = new Date();
  const curY = now.getFullYear();
  const curM = now.getMonth() + 1;
  const curYM = `${curY}-${String(curM).padStart(2, "0")}`;
  const [authed, setAuthed] = useState(false);
  const [data, setData] = useState<AnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const { push: toastPush } = useToast();

  useEffect(() => {
    if (error) toastPush(error, "danger");
  }, [error, toastPush]);
  const [year, setYear] = useState(curY);
  const [month, setMonth] = useState(curM);
  const [txs, setTxs] = useState<any[]>([]);
  const [txCategory, setTxCategory] = useState<string>("");
  const [txQuery, setTxQuery] = useState<string>("");
  const [editingTxId, setEditingTxId] = useState<number | null>(null);
  const [editItem, setEditItem] = useState("");
  const [editAmount, setEditAmount] = useState("");
  const [editCategory, setEditCategory] = useState("");
  const [txBusy, setTxBusy] = useState(false);

  // ── Budget state ──
  const [userBudgets, setUserBudgets] = useState<any[]>([]);
  const [budgetFormOpen, setBudgetFormOpen] = useState(false);
  const [editingBudgetId, setEditingBudgetId] = useState<number | null>(null);
  const [budgetCat, setBudgetCat] = useState("");
  const [budgetLimit, setBudgetLimit] = useState("");
  const [budgetBusy, setBudgetBusy] = useState(false);

  async function loadBudgets() {
    try {
      const b = await api.budgets.list();
      setUserBudgets(b || []);
    } catch { /* optional */ }
  }

  async function saveBudget() {
    if (!budgetCat.trim() || !budgetLimit) { setError("Category and limit are required."); return; }
    setBudgetBusy(true);
    setError("");
    try {
      if (editingBudgetId) {
        await api.budgets.update(editingBudgetId, { category: budgetCat.trim(), limit_amount: Number(budgetLimit) });
      } else {
        await api.budgets.create({ category: budgetCat.trim(), limit_amount: Number(budgetLimit) });
      }
      setBudgetFormOpen(false);
      setEditingBudgetId(null);
      setBudgetCat("");
      setBudgetLimit("");
      await loadBudgets();
      await load(year, month); // refresh analytics to recalc spent
    } catch (e: any) {
      setError(e.message || "Failed to save budget.");
    } finally {
      setBudgetBusy(false);
    }
  }

  async function deleteBudget(id: number) {
    if (!confirm("Delete this budget?")) return;
    setError("");
    try {
      await api.budgets.delete(id);
      await loadBudgets();
      await load(year, month);
    } catch (e: any) {
      setError(e.message || "Failed to delete budget.");
    }
  }

  async function saveTx(id: number) {
    setTxBusy(true);
    setError("");
    try {
      await api.transactions.update(id, {
        item: editItem.trim() || undefined,
        amount: editAmount ? Number(editAmount) : undefined,
        category: editCategory.trim() || undefined,
      });
      setEditingTxId(null);
      await loadTransactions(txCategory, txQuery);
    } catch (e: any) {
      setError(e.message || "Failed to update transaction.");
    } finally {
      setTxBusy(false);
    }
  }

  async function deleteTx(id: number) {
    if (!confirm("Delete this transaction? This cannot be undone.")) return;
    setTxBusy(true);
    setError("");
    try {
      await api.transactions.delete(id);
      await loadTransactions(txCategory, txQuery);
    } catch (e: any) {
      setError(e.message || "Failed to delete transaction.");
    } finally {
      setTxBusy(false);
    }
  }

  const loadTransactions = useCallback(async (cat: string, q: string) => {
    try {
      const data = await api.transactions.list({ category: cat || null, q: q || null, limit: 200 });
      setTxs(data.transactions || []);
    } catch {
      /* transactions optional */
    }
  }, []);

  const load = useCallback(async (y: number, m: number) => {
    setLoading(true);
    setError("");
    try {
      const d = await api.analytics.get(y, m);
      setData(d);
    } catch (e: any) {
      setError(e.message || "Failed to load analytics.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getSession().then(({ data: s }) => {
      if (s.session) {
        setAuthed(true);
        load(curY, curM);
        loadTransactions("", "");
        loadBudgets();
      } else if (isGuest()) {
        setAuthed(true);
        load(curY, curM);
        loadTransactions("", "");
        loadBudgets();
      } else {
        setAuthed(false);
      }
    });
  }, [load, loadTransactions]);

  function shift(delta: number) {
    setMonth((m) => {
      let nm = m + delta;
      let ny = year;
      if (nm <= 0) { nm = 12; ny -= 1; }
      else if (nm > 12) { nm = 1; ny += 1; }
      setYear(ny);
      load(ny, nm);
      return nm;
    });
  }
  function resetMonth() {
    setYear(0);
    setMonth(0);
    load(0, 0);
  }

  if (!authed) {
    return (
      <PageShell active="/analytics">
        <div className="mx-auto max-w-md">
          <div className="rounded-2xl p-8 text-center" style={{ background: "var(--purch-paper)", boxShadow: "var(--purch-shadow-sm)" }}>
            <h1 className="font-sans font-semibold text-[30px] m-0 mb-2">Analytics</h1>
            <p className="text-[14px] text-[color:var(--purch-muted-ink)] m-0">Sign in to see your spending overview.</p>
            <a href="/" className={`${outlineButton} mt-4`}>Sign in</a>
          </div>
        </div>
      </PageShell>
    );
  }

  if (loading && !data) {
    return (
      <PageShell active="/analytics">
        <div className="flex flex-col items-center justify-center gap-4 py-24">
          <div
            className="h-10 w-10 rounded-full border-2 border-[color:var(--purch-line)] border-t-[color:var(--purch-accent)] animate-spin"
            role="status"
            aria-label="Loading"
          />
          <p className="font-sans text-[14px] text-[color:var(--purch-muted-ink)] animate-pulse">
            Crunching your numbers…
          </p>
        </div>
      </PageShell>
    );
  }

  const d = data;
  const monthLabel = d?.month_label || "This month";
  const [mlabel = "August", myear = "2026"] = monthLabel.split(" ");
  const trendBars = d?.trend?.map((p) => p.total) ?? [];
  const peak = d?.trend_peak ?? 0;

  // Distinct categories across analytics + loaded transactions, for the filter.
  const txCategories = Array.from(
    new Set([
      ...(d?.categories?.map((c) => c.category) || []),
      ...(txs?.map((t) => t.category) || []),
    ])
  ).filter(Boolean).sort();

  const filteredTxs = (txs || []).filter((t) => {
    if (txCategory && t.category !== txCategory) return false;
    if (txQuery.trim()) {
      const q = txQuery.toLowerCase();
      if (!t.item.toLowerCase().includes(q) && !t.category.toLowerCase().includes(q)) return false;
    }
    return true;
  });

  return (
    <PageShell active="/analytics">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-6">
        <div>
          <div className={eyebrow}>Spending overview</div>
          <h1 className="font-sans font-semibold text-[30px] mt-0 m-0">
            Analytics
          </h1>
        </div>
        <div className="flex gap-2.5 items-center">
          <select
            value={`${year}-${String(month).padStart(2, "0")}`}
            onChange={(e) => {
              const [ny, nm] = e.target.value.split("-").map(Number);
              setYear(ny);
              setMonth(nm);
              load(ny, nm);
            }}
            className="rounded-lg border px-3.5 py-2.5 text-[13px] font-semibold bg-white"
            style={{ borderColor: "var(--purch-line)" }}
          >
            {(() => {
              const months = Array.from(
                new Set([curYM, ...(d?.available_months || [])])
              ).sort().reverse();
              return months.map((m) => {
                const [my, mm] = m.split("-").map(Number);
                return <option key={m} value={m}>{MONTHS[mm - 1]} {my}</option>;
              });
            })()}
          </select>
          <button onClick={() => load(year, month)} disabled={loading} className={`${outlineButton} text-[13px] disabled:opacity-60`}>
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-3 mb-4 p-3 rounded-lg border" style={{ borderColor: "var(--purch-rust)", background: "var(--purch-paper)" }}>
          <span style={{ color: "var(--purch-rust)" }}><AlertTriangle size={14} strokeWidth={1.5} /></span>
          <p className="text-sm flex-1 m-0">{error}</p>
        </div>
      )}

      {d?.unavailable ? (
        <div className="rounded-lg border p-10 text-center text-[color:var(--purch-taupe)] italic" style={{ background: "var(--purch-paper)", borderColor: "var(--purch-line)" }}>
          Analytics is temporarily unavailable. Try again in a moment.
        </div>
      ) : (
        <>
          {/* KPI row */}
          <FadeInSection className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 mb-5">
            <KpiCard
              label="Spent this month"
              value={d?.kpi.total ?? 0}
              note={(d?.kpi.tx_count ?? 0) > 0 ? `${d?.kpi.tx_count} transaction${(d?.kpi.tx_count ?? 0) === 1 ? "" : "s"}` : "No transactions yet"}
              color="var(--purch-ink)"
              isNumber
              prefix="₱"
            />
            <KpiCard
              label="Transactions"
              value={d?.kpi.tx_count ?? 0}
              note="Logged this month"
              isNumber
            />
            <KpiCard
              label="Top category"
              value={d?.top_category || "—"}
              note={(d?.top_category_amount ?? 0) > 0 ? `₱${d?.top_category_amount?.toLocaleString()} in ${mlabel}` : "No spending yet"}
              color="var(--purch-ink)"
            />
            <KpiCard
              label="Budget used"
              value={`${(d?.budget_used_pct ?? 0).toFixed(0)}%`}
              note={(d?.budget_limit_total ?? 0) > 0 ? `₱${d?.budget_spent_total?.toLocaleString()} of ₱${d?.budget_limit_total?.toLocaleString()}` : "Set one in chat"}
              color={(d?.budget_used_pct ?? 0) >= 100 ? "var(--purch-coral)" : (d?.budget_used_pct ?? 0) >= 80 ? "var(--purch-gold)" : "var(--purch-ink)"}
            />
          </FadeInSection>

          <FadeInSection className="grid grid-cols-1 lg:grid-cols-2 gap-3.5" delay={100}>
            {/* Category breakdown */}
            <div className="rounded-2xl p-5" style={{ background: "var(--purch-paper)", boxShadow: "var(--purch-shadow-sm)" }}>
              <h3 className="font-sans font-semibold text-lg m-0 mb-3.5">Category breakdown</h3>
              {d && d.categories.length > 0 ? (
                d.categories.map((c) => (
                  <div key={c.category} className="mb-3.5 last:mb-0">
                    <div className="flex justify-between text-[13px] mb-1.5">
                      <span style={{ color: "var(--purch-ink)" }}>{c.category}</span>
                      <span className="font-['JetBrains_Mono']" style={{ color: "var(--purch-ink)" }}>₱{c.total.toLocaleString()}</span>
                    </div>
                    <div className="h-2 rounded-full" style={{ background: "var(--purch-line)" }}>
                      <div className="h-full rounded-full" style={{ width: `${Math.min(c.pct_of_total, 100)}%`, background: "var(--purch-accent)" }} />
                    </div>
                    <div className="text-[11.5px] text-[color:var(--purch-muted-ink)] mt-1.5">
                      {c.pct_of_total.toFixed(0)}% of monthly spend
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-[color:var(--purch-muted-ink)] italic py-6 text-center m-0">
                  No spending logged for this month — try &quot;coffee 150&quot; in chat.
                </p>
              )}
            </div>

            {/* Trend — line chart */}
            <div className="rounded-2xl p-5" style={{ background: "var(--purch-paper)", boxShadow: "var(--purch-shadow-sm)" }}>
              <h3 className="font-sans font-semibold text-lg m-0 mb-3.5">Spending trend</h3>
              <SpendingLineChart trend={d?.trend ?? []} peak={peak} monthLabel={mlabel} />
            </div>
          </FadeInSection>

          {/* Budgets */}
          {d && d.budgets.length > 0 && (
            <FadeInSection className="mt-4" delay={200}>
              <h3 className="font-sans font-semibold text-lg mb-3">Budget status</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
                {d.budgets.map((b, i) => {
                  const fill =
                    b.status === "over" ? "var(--purch-coral)" : b.status === "near" ? "var(--purch-gold)" : "var(--purch-accent)";
                  return (
                    <div key={i} className="rounded-2xl p-5" style={{ background: "var(--purch-paper)", boxShadow: "var(--purch-shadow-sm)" }}>
                      <div className="flex justify-between items-center mb-3">
                        <h4 className="font-sans font-semibold text-base m-0" style={{ color: "var(--purch-ink)" }}>{b.category}</h4>
                        <span
                          className="text-[0.6rem] font-bold uppercase tracking-wider px-2 py-0.5 rounded"
                          style={{
                            background: b.status === "over" ? "rgba(255,69,58,0.12)" : b.status === "near" ? "rgba(255,176,32,0.15)" : "rgba(10,132,255,0.15)",
                            color: b.status === "over" ? "var(--purch-coral)" : b.status === "near" ? "var(--purch-gold)" : "var(--purch-accent)",
                          }}
                        >
                          {b.status === "over" ? "Over budget" : b.status === "near" ? "Almost there" : "On track"}
                        </span>
                      </div>
                      <div className="flex items-baseline mb-2">
                        <span className="font-['JetBrains_Mono'] text-2xl font-bold" style={{ color: "var(--purch-ink)" }}>₱{b.spent.toLocaleString()}</span>
                        <span className="font-['JetBrains_Mono'] text-xs text-[color:var(--purch-muted-ink)] ml-1">/ ₱{b.limit_amount.toLocaleString()}</span>
                      </div>
                      <div className="h-1.5 rounded-full" style={{ background: "var(--purch-line)" }}>
                        <div className="h-full rounded-full" style={{ width: `${Math.min(b.pct, 100)}%`, background: fill }} />
                      </div>
                      <div className="flex justify-between mt-1.5 text-[11.5px]">
                        <span className="font-['JetBrains_Mono] text-[color:var(--purch-muted-ink)]">{b.pct.toFixed(0)}% used</span>
                        {b.remaining >= 0 ? (
                          <span className="font-['JetBrains_Mono] text-[color:var(--purch-teal)]">₱{b.remaining.toLocaleString()} left</span>
                        ) : (
                          <span className="font-['JetBrains_Mono] text-[color:var(--purch-coral)]">₱{(-b.remaining).toLocaleString()} over</span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </FadeInSection>
          )}

          {/* ── User Budgets — add/edit/delete ── */}
          <FadeInSection className="mt-4 rounded-2xl p-5" style={{ background: "var(--purch-paper)", boxShadow: "var(--purch-shadow-sm)" }} delay={250}>
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-sans font-semibold text-lg m-0">Your budgets</h3>
              <button
                onClick={() => { setEditingBudgetId(null); setBudgetCat(""); setBudgetLimit(""); setBudgetFormOpen(!budgetFormOpen); }}
                className="purch-btn-primary text-[13px] font-medium rounded-full px-4 py-1.5"
              >
                {budgetFormOpen ? "Cancel" : "+ Add budget"}
              </button>
            </div>

            {/* Add / Edit form */}
            {budgetFormOpen && (
              <div className="flex flex-col sm:flex-row gap-2.5 mb-4 p-3 rounded-xl" style={{ background: "var(--purch-line)", border: "1px solid var(--purch-line)" }}>
                <input
                  value={budgetCat}
                  onChange={(e) => setBudgetCat(e.target.value)}
                  placeholder="Category name (e.g. Food)"
                  className="flex-1 rounded-lg px-3 py-2 text-sm bg-white outline-none"
                  style={{ border: "1px solid var(--purch-line)", color: "var(--purch-ink)" }}
                />
                <input
                  type="number"
                  value={budgetLimit}
                  onChange={(e) => setBudgetLimit(e.target.value)}
                  placeholder="Monthly limit (₱)"
                  className="w-full sm:w-40 rounded-lg px-3 py-2 text-sm bg-white outline-none"
                  style={{ border: "1px solid var(--purch-line)", color: "var(--purch-ink)" }}
                />
                <button
                  onClick={saveBudget}
                  disabled={budgetBusy}
                  className="purch-btn-primary text-[13px] font-medium rounded-full px-5 py-2 disabled:opacity-60"
                >
                  {budgetBusy ? "Saving…" : editingBudgetId ? "Update" : "Save"}
                </button>
              </div>
            )}

            {/* Budget list */}
            {userBudgets.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {userBudgets.map((b) => (
                  <div key={b.id} className="rounded-xl p-4 flex flex-col gap-2" style={{ background: "white", border: "1px solid var(--purch-line)" }}>
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-sm" style={{ color: "var(--purch-ink)" }}>{b.category}</span>
                      <div className="flex gap-1.5">
                        <button
                          onClick={() => { setEditingBudgetId(b.id); setBudgetCat(b.category); setBudgetLimit(String(b.limit_amount)); setBudgetFormOpen(true); }}
                          className="text-[11px] px-2 py-0.5 rounded-full hover:bg-[var(--purch-line)] transition-colors"
                          style={{ color: "var(--purch-muted-ink)" }}
                        >Edit</button>
                        <button
                          onClick={() => deleteBudget(b.id)}
                          className="text-[11px] px-2 py-0.5 rounded-full hover:bg-red-50 transition-colors"
                          style={{ color: "var(--purch-coral)" }}
                        >Delete</button>
                      </div>
                    </div>
                    <span className="font-['JetBrains_Mono'] text-lg font-bold" style={{ color: "var(--purch-ink)" }}>₱{b.limit_amount.toLocaleString()}</span>
                    <span className="text-[11px]" style={{ color: "var(--purch-muted-ink)" }}>per {b.period}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm italic m-0" style={{ color: "var(--purch-muted-ink)" }}>
                No budgets yet. Add one to start tracking spending limits per category.
              </p>
            )}
          </FadeInSection>

          {/* All transactions — filter by category + searchable */}
          <FadeInSection className="mt-4 rounded-2xl p-5" style={{ background: "var(--purch-paper)", boxShadow: "var(--purch-shadow-sm)" }} delay={300}>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
              <h3 className="font-sans font-semibold text-lg m-0">All transactions</h3>
              <div className="flex flex-col sm:flex-row gap-2.5">
                <div className="relative">
                  <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[color:var(--purch-muted-ink)]" />
                  <input
                    value={txQuery}
                    onChange={(e) => setTxQuery(e.target.value)}
                    placeholder="Search item or category…"
                    className="h-10 w-full rounded-lg pl-9 pr-3 text-[13px] bg-white sm:w-[220px]"
                    style={{ border: "1px solid var(--purch-line-soft)" }}
                  />
                </div>
                <select
                  value={txCategory}
                  onChange={(e) => setTxCategory(e.target.value)}
                  className="h-10 rounded-lg px-3 text-[13px] font-semibold bg-white"
                  style={{ border: "1px solid var(--purch-line-soft)" }}
                >
                  <option value="">All categories</option>
                  {txCategories.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>
            </div>

            {filteredTxs.length === 0 ? (
              <p className="text-sm text-[color:var(--purch-taupe)] italic py-6 text-center">
                No transactions match your filters.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <div className="max-h-[220px] overflow-y-auto">
                <table className="w-full text-[13px]">
                  <thead className="sticky top-0 bg-[color:var(--purch-paper)]">
                    <tr className="text-left text-[11px] uppercase tracking-[0.08em] text-[color:var(--purch-taupe)] border-b" style={{ borderColor: "var(--purch-line)" }}>
                      <th className="py-2 pr-3 font-semibold">Item</th>
                      <th className="py-2 pr-3 font-semibold">Category</th>
                      <th className="py-2 pr-3 font-semibold">Date</th>
                      <th className="py-2 text-right font-semibold">Amount</th>
                      <th className="py-2 text-right font-semibold">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredTxs.map((t, i) => {
                      const editing = editingTxId === (t.transaction_id ?? -1);
                      return (
                        <tr key={t.transaction_id ?? i} className="border-b last:border-0 align-top" style={{ borderColor: "var(--purch-line-soft)" }}>
                          {editing ? (
                            <>
                              <td className="py-2 pr-3">
                                <input value={editItem} onChange={(e) => setEditItem(e.target.value)} className="w-full rounded-md px-2 py-1 text-[13px]" style={{ border: "1px solid var(--purch-line-soft)" }} />
                              </td>
                              <td className="py-2 pr-3">
                                <input value={editCategory} onChange={(e) => setEditCategory(e.target.value)} className="w-full rounded-md px-2 py-1 text-[13px]" style={{ border: "1px solid var(--purch-line-soft)" }} />
                              </td>
                              <td className="py-2 pr-3 font-['JetBrains_Mono'] text-[12px] text-[color:var(--purch-taupe)] whitespace-nowrap">
                                {t.tx_timestamp?.replace("T", " ") || ""}
                              </td>
                              <td className="py-2 text-right font-['JetBrains_Mono]">
                                <input value={editAmount} onChange={(e) => setEditAmount(e.target.value)} className="w-24 rounded-md px-2 py-1 text-[13px] text-right" style={{ border: "1px solid var(--purch-line-soft)" }} />
                              </td>
                              <td className="py-2 text-right whitespace-nowrap">
                                <button onClick={() => saveTx(t.transaction_id!)} disabled={txBusy} className="text-[12px] font-semibold" style={{ color: "var(--purch-pine)" }}>Save</button>
                                <button onClick={() => setEditingTxId(null)} className="text-[12px] ml-2 text-[color:var(--purch-taupe)] hover:text-[color:var(--purch-ink)]">Cancel</button>
                              </td>
                            </>
                          ) : (
                            <>
                              <td className="py-2.5 pr-3 font-medium">{t.item || "—"}</td>
                              <td className="py-2.5 pr-3">
                                {(() => {
                                  const colors = getCategoryColors(t.category || "");
                                  return (
                                    <span className="text-[11px] px-2 py-0.5 rounded-full font-medium" style={{ background: colors.bg, color: colors.text }}>
                                      {t.category || "Uncategorized"}
                                    </span>
                                  );
                                })()}
                              </td>
                              <td className="py-2.5 pr-3 font-['JetBrains_Mono'] text-[12px] text-[color:var(--purch-taupe)] whitespace-nowrap">
                                {t.tx_timestamp?.replace("T", " ") || ""}
                              </td>
                              <td className="py-2.5 text-right font-['JetBrains_Mono]">
                                {t.amount_display || `₱${(t.amount ?? 0).toFixed(2)}`}
                              </td>
                              <td className="py-2.5 text-right whitespace-nowrap">
                                <button
                                  onClick={() => {
                                    setEditingTxId(t.transaction_id ?? null);
                                    setEditItem(t.item || "");
                                    setEditAmount(String(t.amount ?? ""));
                                    setEditCategory(t.category || "");
                                  }}
                                  className="text-[12px] font-semibold" style={{ color: "var(--purch-pine)" }}
                                >
                                  Edit
                                </button>
                                <button onClick={() => deleteTx(t.transaction_id!)} className="text-[12px] ml-2 text-[color:var(--purch-taupe)] hover:text-[color:var(--purch-rust)]">
                                  Delete
                                </button>
                              </td>
                            </>
                          )}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                </div>
              </div>
            )}
            <div className="flex items-center justify-between text-[11.5px] text-[color:var(--purch-taupe)] mt-3">
              <span>Showing {Math.min(filteredTxs.length, 5)} of {filteredTxs.length} match{filteredTxs.length === 1 ? "" : "es"}</span>
              {filteredTxs.length > 5 && (
                <span className="italic">Scroll to see all — top 5 shown</span>
              )}
            </div>
          </FadeInSection>
        </>
      )}
    </PageShell>
  );
}
