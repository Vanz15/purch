"use client";

import { useEffect, useState, useCallback } from "react";
import { createClient } from "@/lib/supabase/client";
import { api, AnalyticsResponse } from "@/lib/api";
import { PageShell, eyebrow, outlineButton } from "@/lib/ui";

function KpiCard({
  label,
  value,
  hint,
  tone = "default",
}: {
  label: string;
  value: React.ReactNode;
  hint: React.ReactNode;
  tone?: "default" | "coral" | "gold" | "danger";
}) {
  const toneCls =
    tone === "coral"
      ? "text-[color:var(--purch-coral)]"
      : tone === "gold"
      ? "text-[color:var(--purch-gold)]"
      : tone === "danger"
      ? "text-[color:var(--purch-danger)]"
      : "text-[color:var(--purch-ink)]";
  return (
    <div className="purch-card p-5 w-full h-full flex flex-col">
      <div className={eyebrow}>{label}</div>
      <div className={`font-['Playfair_Display'] font-bold text-3xl mt-2 ${toneCls}`}>
        {value}
      </div>
      <div className="text-xs text-[color:var(--purch-muted)] mt-2 leading-relaxed">
        {hint}
      </div>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const map: Record<string, string> = {
    over: "bg-[color:var(--purch-danger)]/10 text-[color:var(--purch-danger)]",
    near: "bg-[color:var(--purch-gold)]/15 text-[color:var(--purch-gold)]",
  };
  const cls = map[status] || "bg-[color:var(--purch-teal)]/15 text-[color:var(--purch-teal)]";
  const label = status === "over" ? "Over budget" : status === "near" ? "Almost there" : "On track";
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[0.6rem] font-bold uppercase tracking-wider ${cls}`}>
      {label}
    </span>
  );
}

export default function AnalyticsPage() {
  const [authed, setAuthed] = useState(false);
  const [data, setData] = useState<AnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [year, setYear] = useState(0);
  const [month, setMonth] = useState(0);

  const load = useCallback(
    async (y: number, m: number) => {
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
    },
    []
  );

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getSession().then(({ data: s }) => {
      if (!s.session) {
        setAuthed(false);
      } else {
        setAuthed(true);
        load(0, 0);
      }
    });
  }, [load]);

  function shift(delta: number) {
    setMonth((m) => {
      let nm = m + delta;
      let ny = year;
      if (nm <= 0) {
        nm = 12;
        ny -= 1;
      } else if (nm > 12) {
        nm = 1;
        ny += 1;
      }
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
        <div className="max-w-6xl mx-auto w-full p-6">
          <div className="purch-card p-8 text-center">
            <h1 className="font-['Playfair_Display'] font-bold text-3xl text-[color:var(--purch-ink)]">
              Analytics
            </h1>
            <p className="text-[color:var(--purch-secondary-text)] mt-2">
              Sign in to see your spending overview.
            </p>
            <a href="/login" className={`${outlineButton} mt-4`}>
              Sign in
            </a>
          </div>
        </div>
      </PageShell>
    );
  }

  if (loading && !data) {
    return (
      <PageShell active="/analytics">
        <div className="max-w-6xl mx-auto w-full p-6">
          <div className="animate-pulse h-40 bg-[color:var(--purch-border)]/60 rounded-2xl" />
        </div>
      </PageShell>
    );
  }

  const d = data;

  return (
    <PageShell active="/analytics">
      <div className="max-w-6xl mx-auto w-full p-6">
        {/* Header + month nav */}
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3 mb-6">
          <div className="flex-1 min-w-0">
            <div className={eyebrow}>Spending overview</div>
            <h1 className="font-['Playfair_Display'] font-bold tracking-tight text-3xl sm:text-4xl text-[color:var(--purch-ink)] mt-1">
              Analytics
            </h1>
            <p className="text-sm text-[color:var(--purch-secondary-text)] mt-2">
              {d?.month_label || "Live data from Supabase"}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1 rounded-xl border border-[color:var(--purch-border)] bg-[color:var(--purch-parchment)] p-1.5">
              <button
                onClick={() => shift(-1)}
                disabled={loading}
                className="w-8 h-8 shrink-0 rounded-lg border border-[color:var(--purch-border)] bg-[color:var(--purch-paper)] text-[color:var(--purch-ink)] text-sm font-semibold hover:border-[color:var(--purch-coral)] hover:text-[color:var(--purch-coral)] transition-colors disabled:opacity-40"
              >
                ←
              </button>
              <div className="px-2 text-center min-w-[8.5rem]">
                <div className={eyebrow}>Viewing</div>
                <div className="font-['Playfair_Display'] font-bold text-sm text-[color:var(--purch-ink)] leading-tight">
                  {d?.month_label || "This month"}
                </div>
              </div>
              <button
                onClick={() => shift(1)}
                disabled={loading}
                className="w-8 h-8 shrink-0 rounded-lg border border-[color:var(--purch-border)] bg-[color:var(--purch-paper)] text-[color:var(--purch-ink)] text-sm font-semibold hover:border-[color:var(--purch-coral)] hover:text-[color:var(--purch-coral)] transition-colors disabled:opacity-40"
              >
                →
              </button>
            </div>
            {(year !== 0 || month !== 0) && (
              <button onClick={resetMonth} disabled={loading} className={`${outlineButton} text-xs py-2 disabled:opacity-60`}>
                This month
              </button>
            )}
            <button onClick={() => load(year, month)} disabled={loading} className={`${outlineButton} text-sm disabled:opacity-60`}>
              {loading ? "Refreshing…" : "↻ Refresh"}
            </button>
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-3 mb-4 p-3 rounded-xl border border-[color:var(--purch-danger)] bg-[color:var(--purch-paper)]">
            <span className="text-[color:var(--purch-danger)] font-bold">⚠</span>
            <p className="text-sm flex-1 m-0">{error}</p>
          </div>
        )}

        {d?.unavailable ? (
          <div className="purch-card p-10 text-center text-[color:var(--purch-muted)] italic">
            Analytics is temporarily unavailable. Try again in a moment.
          </div>
        ) : (
          <>
            {/* KPIs */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 w-full mb-6">
              <KpiCard
                label="Spent this month"
                value={<>₱{d?.kpi.total?.toLocaleString() ?? 0}</>}
                hint={
                  (d?.kpi.tx_count ?? 0) > 0
                    ? `Across ${d?.kpi.tx_count} transactions`
                    : "No transactions yet"
                }
                tone="coral"
              />
              <KpiCard
                label="Transactions"
                value={d?.kpi.tx_count ?? 0}
                hint="Logged this month"
              />
              <KpiCard
                label="Top category"
                value={d?.top_category || "—"}
                hint={
                  (d?.top_category_amount ?? 0) > 0
                    ? `₱${d?.top_category_amount?.toLocaleString()} spent`
                    : "No spending yet"
                }
                tone="gold"
              />
              <KpiCard
                label="Budget used"
                value={<>{(d?.budget_used_pct ?? 0).toFixed(0)}%</>}
                hint={
                  (d?.budget_limit_total ?? 0) > 0
                    ? `₱${d?.budget_spent_total?.toLocaleString()} of ₱${d?.budget_limit_total?.toLocaleString()}`
                    : "Set a budget in chat"
                }
                tone={(d?.budget_used_pct ?? 0) >= 100 ? "danger" : (d?.budget_used_pct ?? 0) >= 80 ? "gold" : "default"}
              />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Category breakdown */}
              <section className="purch-card p-6">
                <div className="flex items-end justify-between gap-3 mb-4">
                  <div>
                    <div className={eyebrow}>Where it went</div>
                    <h2 className="font-['Playfair_Display'] font-bold text-xl sm:text-2xl text-[color:var(--purch-ink)] mt-1">
                      Category breakdown
                    </h2>
                  </div>
                  <span className="text-xs text-[color:var(--purch-muted)]">{d?.month_label}</span>
                </div>
                {d && d.categories.length > 0 ? (
                  d.categories.map((c) => (
                    <div key={c.category} className="mb-4 last:mb-0">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-sm font-semibold text-[color:var(--purch-ink)]">
                          {c.category}
                        </span>
                        <span className="flex items-baseline gap-3">
                          <span className="font-['DM_Mono'] text-[0.65rem] text-[color:var(--purch-muted)]">
                            {c.count} tx
                          </span>
                          <span className="font-['DM_Mono'] text-sm font-semibold text-[color:var(--purch-coral)]">
                            ₱{c.total.toLocaleString()}
                          </span>
                        </span>
                      </div>
                      <div className="h-2 rounded-full bg-[color:var(--purch-border)] overflow-hidden">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-[color:var(--purch-coral)] to-[color:var(--purch-coral-light)]"
                          style={{ width: `${Math.min(c.pct_of_total, 100)}%` }}
                        />
                      </div>
                      <div className="mt-1">
                        <span className="font-['DM_Mono'] text-[0.65rem] text-[color:var(--purch-muted)]">
                          {c.pct_of_total.toFixed(0)}% of monthly spend
                        </span>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-[color:var(--purch-muted)] italic py-8 text-center">
                    No spending logged for this month — try &quot;coffee 150&quot; in chat.
                  </p>
                )}
              </section>

              {/* Trend */}
              <section className="purch-card p-6">
                <div className="flex items-end justify-between gap-3 mb-4">
                  <div>
                    <div className={eyebrow}>Daily spend</div>
                    <h2 className="font-['Playfair_Display'] font-bold text-xl sm:text-2xl text-[color:var(--purch-ink)] mt-1">
                      Spending trend
                    </h2>
                  </div>
                  {d && d.trend_peak > 0 && (
                    <span className="font-['DM_Mono'] text-[0.65rem] text-[color:var(--purch-muted)]">
                      Peak: ₱{d.trend_peak.toLocaleString()}
                    </span>
                  )}
                </div>
                {d && d.trend.length > 0 ? (
                  <>
                    <div className="flex items-end w-full h-40 gap-0.5">
                      {d.trend.map((p, i) => {
                        const ratio = d.trend_peak > 0 ? (p.total / d.trend_peak) * 100 : 0;
                        return (
                          <div
                            key={i}
                            className="flex flex-col justify-end h-full flex-1 min-w-0 px-[1px]"
                            title={p.day}
                          >
                            <div
                              className={
                                p.total > 0
                                  ? "w-full rounded-t-md bg-[color:var(--purch-coral)] transition-all"
                                  : "w-full rounded-t-md bg-[color:var(--purch-border)]"
                              }
                              style={{ height: p.total > 0 ? `${ratio}%` : "3px" }}
                            />
                          </div>
                        );
                      })}
                    </div>
                    <div className="flex items-center justify-between mt-2 pt-2 border-t border-dashed border-[color:var(--purch-border)]">
                      <span className="font-['DM_Mono'] text-[0.6rem] text-[color:var(--purch-muted)]">
                        {d.trend[0]?.day}
                      </span>
                      <span className="font-['DM_Mono'] text-[0.6rem] text-[color:var(--purch-muted)]">
                        {d.trend[d.trend.length - 1]?.day}
                      </span>
                    </div>
                  </>
                ) : (
                  <p className="text-sm text-[color:var(--purch-muted)] italic py-8 text-center">
                    No activity this month — log a purchase to see the trend.
                  </p>
                )}
              </section>
            </div>

            {/* Budgets */}
            {d && d.budgets.length > 0 && (
              <section className="mt-4">
                <div className="flex items-end justify-between gap-3 mb-4">
                  <div>
                    <div className={eyebrow}>Budget status</div>
                    <h2 className="font-['Playfair_Display'] font-bold text-xl sm:text-2xl text-[color:var(--purch-ink)] mt-1">
                      Selected month vs. plan
                    </h2>
                  </div>
                  <span className="font-['DM_Mono'] text-[0.65rem] text-[color:var(--purch-muted)]">
                    {d.budgets.length} active
                  </span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {d.budgets.map((b, i) => {
                    const fillCls =
                      b.status === "over"
                        ? "bg-[color:var(--purch-danger)] h-full rounded-full"
                        : b.status === "near"
                        ? "bg-[color:var(--purch-gold)] h-full rounded-full"
                        : "bg-[color:var(--purch-coral)] h-full rounded-full";
                    return (
                      <div key={i} className="purch-card p-5">
                        <div className="flex items-center justify-between gap-2 mb-3">
                          <h3 className="font-['Playfair_Display'] font-bold text-base text-[color:var(--purch-ink)] m-0">
                            {b.category}
                          </h3>
                          <StatusPill status={b.status} />
                        </div>
                        <div className="flex items-baseline mb-2">
                          <span className="font-['DM_Mono'] text-2xl font-bold text-[color:var(--purch-ink)]">
                            ₱{b.spent.toLocaleString()}
                          </span>
                          <span className="font-['DM_Mono'] text-xs text-[color:var(--purch-muted)] ml-1">
                            / ₱{b.limit_amount.toLocaleString()}
                          </span>
                        </div>
                        <div className="h-2 rounded-full bg-[color:var(--purch-border)] overflow-hidden">
                          <div className={fillCls} style={{ width: `${Math.min(b.pct, 100)}%` }} />
                        </div>
                        <div className="flex items-center justify-between mt-1.5">
                          <span className="font-['DM_Mono'] text-[0.65rem] text-[color:var(--purch-muted)]">
                            {b.pct.toFixed(0)}% used
                          </span>
                          {b.remaining >= 0 ? (
                            <span className="font-['DM_Mono'] text-[0.65rem] text-[color:var(--purch-teal)]">
                              ₱{b.remaining.toLocaleString()} left
                            </span>
                          ) : (
                            <span className="font-['DM_Mono'] text-[0.65rem] text-[color:var(--purch-danger)]">
                              ₱{(-b.remaining).toLocaleString()} over
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            )}

            {/* Recent transactions */}
            {d && d.recent.length > 0 && (
              <section className="mt-4 purch-card p-6">
                <div className={eyebrow}>Recent</div>
                <h2 className="font-['Playfair_Display'] font-bold text-xl sm:text-2xl text-[color:var(--purch-ink)] mt-1 mb-4">
                  Latest transactions
                </h2>
                <div className="divide-y divide-[color:var(--purch-border)]">
                  {d.recent.slice(0, 8).map((t, i) => (
                    <div key={i} className="flex items-center justify-between py-3">
                      <div>
                        <div className="text-sm font-medium text-[color:var(--purch-ink)]">
                          {t.item}
                        </div>
                        <div className="text-xs text-[color:var(--purch-muted)]">{t.category}</div>
                      </div>
                      <div className="text-right">
                        <div className="font-['DM_Mono'] text-sm font-semibold text-[color:var(--purch-coral)]">
                          ₱{t.amount.toLocaleString()}
                        </div>
                        <div className="text-xs text-[color:var(--purch-muted)]">
                          {new Date(t.tx_timestamp).toLocaleDateString()}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </div>
    </PageShell>
  );
}
