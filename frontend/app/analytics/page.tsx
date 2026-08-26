"use client";

import { useEffect, useState, useCallback } from "react";
import { ChevronLeft, ChevronRight, RefreshCw, Search } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { api, AnalyticsResponse, TransactionRow } from "@/lib/api";
import { PageShell, eyebrow, outlineButton } from "@/lib/ui";
import { ChatSidebar } from "@/components/ChatSidebar";
import { isGuest } from "@/lib/guest";

const MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"];

function KpiCard({ label, value, note, color }: { label: string; value: React.ReactNode; note: string; color?: string }) {
  return (
    <div className="rounded-lg border p-4" style={{ background: "var(--purch-paper)", borderColor: "var(--purch-line)" }}>
      <div className={eyebrow} style={{ fontSize: 11 }}>{label}</div>
      <div className="font-['Fraunces'] font-semibold text-[26px] mt-2 mb-1" style={{ color: color || "var(--purch-ink)" }}>
        {value}
      </div>
      <div className="text-[11.5px] text-[color:var(--purch-taupe)]">{note}</div>
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
  const [year, setYear] = useState(curY);
  const [month, setMonth] = useState(curM);
  const [txs, setTxs] = useState<TransactionRow[]>([]);
  const [txCategory, setTxCategory] = useState<string>("");
  const [txQuery, setTxQuery] = useState<string>("");

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
      } else if (isGuest()) {
        setAuthed(true);
        load(curY, curM);
        loadTransactions("", "");
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
      <PageShell active="/analytics" sidebar={<ChatSidebar />}>
        <div className="mx-auto max-w-md">
          <div className="rounded-lg p-8 text-center" style={{ background: "var(--purch-paper)", boxShadow: "var(--purch-shadow-sm)" }}>
            <h1 className="font-['Fraunces'] font-semibold text-3xl m-0 mb-2">Analytics</h1>
            <p className="text-[color:var(--purch-taupe)] text-sm">Sign in to see your spending overview.</p>
            <a href="/login" className={`${outlineButton} mt-4`}>Sign in</a>
          </div>
        </div>
      </PageShell>
    );
  }

  if (loading && !data) {
    return (
      <PageShell active="/analytics" sidebar={<ChatSidebar />}>
        <div className="flex flex-col items-center justify-center gap-4 py-24">
          <div
            className="h-10 w-10 rounded-full border-2 border-[color:var(--purch-line)] border-t-[color:var(--purch-rust)] animate-spin"
            role="status"
            aria-label="Loading"
          />
          <p className="font-['Fraunces'] text-[15px] text-[color:var(--purch-taupe)] animate-pulse">
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
    <PageShell active="/analytics" sidebar={<ChatSidebar />}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-6">
        <div>
          <div className={eyebrow}>Spending overview</div>
          <h1 className="font-['Fraunces'] font-semibold text-[30px] mt-0 m-0">
            Analytics
          </h1>
        </div>
        <div className="flex gap-2.5 items-center">
          <select
            value={`${year}-${month}`}
            onChange={(e) => {
              const [ny, nm] = e.target.value.split("-").map(Number);
              setYear(ny);
              setMonth(nm);
              load(ny, nm);
            }}
            className="rounded-lg border px-3.5 py-2.5 text-[13px] font-semibold bg-[color:var(--purch-paper)]"
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
          <span className="font-bold" style={{ color: "var(--purch-rust)" }}>⚠</span>
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
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 mb-5">
            <KpiCard
              label="Spent this month"
              value={<>₱{(d?.kpi.total ?? 0).toLocaleString()}</>}
              note={(d?.kpi.tx_count ?? 0) > 0 ? `${d?.kpi.tx_count} transaction${(d?.kpi.tx_count ?? 0) === 1 ? "" : "s"}` : "No transactions yet"}
              color="var(--purch-rust)"
            />
            <KpiCard label="Transactions" value={d?.kpi.tx_count ?? 0} note="Logged this month" />
            <KpiCard
              label="Top category"
              value={d?.top_category || "—"}
              note={(d?.top_category_amount ?? 0) > 0 ? `₱${d?.top_category_amount?.toLocaleString()} in ${mlabel}` : "No spending yet"}
              color="var(--purch-rust)"
            />
            <KpiCard
              label="Budget used"
              value={`${(d?.budget_used_pct ?? 0).toFixed(0)}%`}
              note={(d?.budget_limit_total ?? 0) > 0 ? `₱${d?.budget_spent_total?.toLocaleString()} of ₱${d?.budget_limit_total?.toLocaleString()}` : "Set one in chat"}
              color={(d?.budget_used_pct ?? 0) >= 100 ? "var(--purch-rust)" : (d?.budget_used_pct ?? 0) >= 80 ? "var(--purch-gold)" : "var(--purch-ink)"}
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3.5">
            {/* Category breakdown */}
            <div className="rounded-lg border p-5" style={{ background: "var(--purch-paper)", borderColor: "var(--purch-line)" }}>
              <h3 className="font-['Fraunces'] font-semibold text-lg m-0 mb-3.5">Category breakdown</h3>
              {d && d.categories.length > 0 ? (
                d.categories.map((c) => (
                  <div key={c.category} className="mb-3.5 last:mb-0">
                    <div className="flex justify-between text-[13px] mb-1.5">
                      <span>{c.category}</span>
                      <span className="font-['JetBrains_Mono']">₱{c.total.toLocaleString()}</span>
                    </div>
                    <div className="h-2 rounded-full" style={{ background: "var(--purch-bg)" }}>
                      <div className="h-full rounded-full" style={{ width: `${Math.min(c.pct_of_total, 100)}%`, background: "var(--purch-rust)" }} />
                    </div>
                    <div className="text-[11.5px] text-[color:var(--purch-taupe)] mt-1.5">
                      {c.pct_of_total.toFixed(0)}% of monthly spend
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-[color:var(--purch-taupe)] italic py-6 text-center">
                  No spending logged for this month — try &quot;coffee 150&quot; in chat.
                </p>
              )}
            </div>

            {/* Trend */}
            <div className="rounded-lg border p-5" style={{ background: "var(--purch-paper)", borderColor: "var(--purch-line)" }}>
              <h3 className="font-['Fraunces'] font-semibold text-lg m-0 mb-3.5">Spending trend</h3>
              {d && d.trend.length > 0 ? (
                <>
                  <div className="flex items-end gap-[3px] h-[90px]">
                    {d.trend.map((p, i) => {
                      const ratio = peak > 0 ? (p.total / peak) * 100 : 0;
                      const isLast = i === d.trend.length - 1;
                      return (
                        <div
                          key={i}
                          className="flex-1 rounded-sm"
                          style={{
                            height: p.total > 0 ? `${Math.max(ratio, 4)}%` : "4%",
                            background: isLast ? "var(--purch-rust)" : "var(--purch-line)",
                          }}
                          title={p.day}
                        />
                      );
                    })}
                  </div>
                  <div className="flex justify-between text-[11px] text-[color:var(--purch-taupe)] mt-2">
                    <span>Aug 01</span>
                    <span>{mlabel} {d.trend[d.trend.length - 1]?.day?.replace(/^\w+,?\s*/, "") || ""}</span>
                  </div>
                </>
              ) : (
                <p className="text-sm text-[color:var(--purch-taupe)] italic py-6 text-center">
                  No activity this month — log a purchase to see the trend.
                </p>
              )}
            </div>
          </div>

          {/* Budgets */}
          {d && d.budgets.length > 0 && (
            <div className="mt-4">
              <h3 className="font-['Fraunces'] font-semibold text-lg mb-3">Budget status</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
                {d.budgets.map((b, i) => {
                  const fill =
                    b.status === "over" ? "var(--purch-rust)" : b.status === "near" ? "var(--purch-gold)" : "var(--purch-rust)";
                  return (
                    <div key={i} className="rounded-lg border p-5" style={{ background: "var(--purch-paper)", borderColor: "var(--purch-line)" }}>
                      <div className="flex justify-between items-center mb-3">
                        <h4 className="font-['Fraunces'] font-semibold text-base m-0">{b.category}</h4>
                        <span
                          className="text-[0.6rem] font-bold uppercase tracking-wider px-2 py-0.5 rounded"
                          style={{
                            background: b.status === "over" ? "rgba(194,78,43,0.12)" : b.status === "near" ? "rgba(232,179,61,0.15)" : "rgba(47,110,92,0.15)",
                            color: b.status === "over" ? "var(--purch-rust)" : b.status === "near" ? "var(--purch-gold)" : "var(--purch-pine)",
                          }}
                        >
                          {b.status === "over" ? "Over budget" : b.status === "near" ? "Almost there" : "On track"}
                        </span>
                      </div>
                      <div className="flex items-baseline mb-2">
                        <span className="font-['JetBrains_Mono'] text-2xl font-bold">₱{b.spent.toLocaleString()}</span>
                        <span className="font-['JetBrains_Mono'] text-xs text-[color:var(--purch-taupe)] ml-1">/ ₱{b.limit_amount.toLocaleString()}</span>
                      </div>
                      <div className="h-1.5 rounded-full" style={{ background: "var(--purch-line)" }}>
                        <div className="h-full rounded-full" style={{ width: `${Math.min(b.pct, 100)}%`, background: fill }} />
                      </div>
                      <div className="flex justify-between mt-1.5 text-[11.5px]">
                        <span className="font-['JetBrains_Mono] text-[color:var(--purch-taupe)]">{b.pct.toFixed(0)}% used</span>
                        {b.remaining >= 0 ? (
                          <span className="font-['JetBrains_Mono] text-[color:var(--purch-pine)]">₱{b.remaining.toLocaleString()} left</span>
                        ) : (
                          <span className="font-['JetBrains_Mono] text-[color:var(--purch-rust)]">₱{(-b.remaining).toLocaleString()} over</span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* All transactions — filter by category + searchable */}
          <div className="mt-4 rounded-lg border p-5" style={{ background: "var(--purch-paper)", borderColor: "var(--purch-line)" }}>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
              <h3 className="font-['Fraunces'] font-semibold text-lg m-0">All transactions</h3>
              <div className="flex flex-col sm:flex-row gap-2.5">
                <div className="relative">
                  <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[color:var(--purch-taupe)]" />
                  <input
                    value={txQuery}
                    onChange={(e) => setTxQuery(e.target.value)}
                    placeholder="Search item or category…"
                    className="h-10 w-full rounded-lg pl-9 pr-3 text-[13px] bg-[color:var(--purch-paper)] sm:w-[220px]"
                    style={{ border: "1px solid var(--purch-line-soft)" }}
                  />
                </div>
                <select
                  value={txCategory}
                  onChange={(e) => setTxCategory(e.target.value)}
                  className="h-10 rounded-lg px-3 text-[13px] font-semibold bg-[color:var(--purch-paper)]"
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
                <table className="w-full text-[13px]">
                  <thead>
                    <tr className="text-left text-[11px] uppercase tracking-[0.08em] text-[color:var(--purch-taupe)] border-b" style={{ borderColor: "var(--purch-line)" }}>
                      <th className="py-2 pr-3 font-semibold">Item</th>
                      <th className="py-2 pr-3 font-semibold">Category</th>
                      <th className="py-2 pr-3 font-semibold">Date</th>
                      <th className="py-2 text-right font-semibold">Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredTxs.map((t, i) => (
                      <tr key={t.transaction_id ?? i} className="border-b last:border-0" style={{ borderColor: "var(--purch-line-soft)" }}>
                        <td className="py-2.5 pr-3 font-medium">{t.item || "—"}</td>
                        <td className="py-2.5 pr-3">
                          <span className="text-[11px] px-2 py-0.5 rounded" style={{ background: "#DCEDE6", color: "var(--purch-pine)" }}>
                            {t.category || "Uncategorized"}
                          </span>
                        </td>
                        <td className="py-2.5 pr-3 font-['JetBrains_Mono'] text-[12px] text-[color:var(--purch-taupe)] whitespace-nowrap">
                          {t.tx_timestamp?.replace("T", " ") || ""}
                        </td>
                        <td className="py-2.5 text-right font-['JetBrains_Mono']">
                          {t.amount_display || `₱${(t.amount ?? 0).toFixed(2)}`}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <div className="text-[11.5px] text-[color:var(--purch-taupe)] mt-3">
              Showing {filteredTxs.length} of {txs?.length ?? 0} transaction{txs?.length === 1 ? "" : "s"}
            </div>
          </div>
        </>
      )}
    </PageShell>
  );
}
