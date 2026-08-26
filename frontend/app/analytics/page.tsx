"use client";

import { useEffect, useState, useCallback } from "react";
import { ChevronLeft, ChevronRight, RefreshCw } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { api, AnalyticsResponse } from "@/lib/api";
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
  const [authed, setAuthed] = useState(false);
  const [data, setData] = useState<AnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [year, setYear] = useState(0);
  const [month, setMonth] = useState(0);

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
        load(0, 0);
      } else if (isGuest()) {
        setAuthed(true);
        load(0, 0);
      } else {
        setAuthed(false);
      }
    });
  }, [load]);

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
        <div className="animate-pulse h-40 rounded-2xl" style={{ background: "var(--purch-line)" }} />
      </PageShell>
    );
  }

  const d = data;
  const monthLabel = d?.month_label || "This month";
  const [mlabel = "August", myear = "2026"] = monthLabel.split(" ");
  const trendBars = d?.trend?.map((p) => p.total) ?? [];
  const peak = d?.trend_peak ?? 0;

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
          <div className="flex items-center gap-2 rounded-lg border px-3.5 py-2.5" style={{ background: "var(--purch-paper)", borderColor: "var(--purch-line)" }}>
            <ChevronLeft size={14} className="cursor-pointer" onClick={() => shift(-1)} />
            <span className="text-[13px] font-semibold">{monthLabel}</span>
            <ChevronRight size={14} className="cursor-pointer" onClick={() => shift(1)} />
          </div>
          {(year !== 0 || month !== 0) && (
            <button onClick={resetMonth} disabled={loading} className={`${outlineButton} text-[13px] disabled:opacity-60`}>
              This month
            </button>
          )}
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
        </>
      )}
    </PageShell>
  );
}
