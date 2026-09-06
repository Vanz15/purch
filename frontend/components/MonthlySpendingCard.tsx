"use client";

import { useEffect, useState } from "react";
import { api, AnalyticsResponse } from "@/lib/api";

const DAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export function MonthlySpendingCard() {
  const [data, setData] = useState<AnalyticsResponse | null>(null);

  async function load() {
    const now = new Date();
    try {
      const a = await api.analytics.get(now.getFullYear(), now.getMonth() + 1);
      setData(a);
    } catch {
      /* keep previous state on failure */
    }
  }

  useEffect(() => {
    load();
    const onRefresh = () => load();
    window.addEventListener("purch:refresh-sidebar", onRefresh);
    return () => window.removeEventListener("purch:refresh-sidebar", onRefresh);
  }, []);

  const trend = data?.trend ?? [];

  // Build 7 bars for the last 7 days from today
  const today = new Date();
  const dayTotals = new Array(7).fill(0);
  const dayLabels: string[] = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    const dateStr = d.toISOString().split("T")[0];
    const label = d.toLocaleDateString("en-US", { weekday: "short" });
    dayLabels.push(label);
    const entry = trend.find((p) => {
      const pDate = (p.iso || p.day || "").split("T")[0].split(" ")[0];
      return pDate === dateStr;
    });
    if (entry) {
      const idx = 6 - i;
      dayTotals[idx] = Math.abs(entry.total);
    }
  }
  const dayPeak = Math.max(...dayTotals, 1);

  // Sum of last 7 days
  const weekTotal = dayTotals.reduce((a, b) => a + b, 0);

  return (
    <div
      className="rounded-2xl p-5 flex flex-col"
      style={{ background: "var(--purch-paper)", boxShadow: "var(--purch-shadow-md)", border: "1px solid var(--purch-line)" }}
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-sans font-bold text-[20px] m-0">Last 7 Days</h3>
      </div>

      {trend.length > 0 ? (
        <>
          {/* Summary */}
          <div className="flex items-center justify-between mb-3">
            <div>
              <div className="text-[10px] text-[color:var(--purch-muted-ink)]">Total</div>
              <div className="font-['JetBrains_Mono'] text-[14px] font-bold" style={{ color: "var(--purch-ink)" }}>
                ₱{weekTotal.toLocaleString()}
              </div>
            </div>
            <div className="text-right">
              <div className="text-[10px] text-[color:var(--purch-muted-ink)]">Transactions</div>
              <div className="font-['JetBrains_Mono'] text-[14px] font-bold" style={{ color: "var(--purch-ink)" }}>
                {data?.kpi?.tx_count ?? 0}
              </div>
            </div>
          </div>

          {/* Bar chart — 7 bars for last 7 days */}
          <div className="flex items-end gap-[6px] h-[80px] px-2 mt-3">
            {dayTotals.map((total, i) => {
              const barHeight = total > 0 ? Math.max((total / dayPeak) * 72, 8) : 4;
              const isToday = today.getDay() === i;
              return (
                <div key={i} className="flex-1 flex flex-col items-center justify-end">
                  <div
                    className="w-full max-w-[28px] rounded-t-md transition-all"
                    style={{
                      height: `${barHeight}px`,
                      background: isToday
                        ? "linear-gradient(180deg, #A78BFA 0%, #8B5CF6 100%)"
                        : "linear-gradient(180deg, #C4B5FD 0%, #A78BFA 100%)",
                      boxShadow: isToday ? "0 0 6px rgba(139, 92, 246, 0.3)" : "none",
                      opacity: total > 0 ? 0.9 : 0.3,
                    }}
                    title={`${DAY_LABELS[i]}: ₱${total.toLocaleString()}`}
                  />
                </div>
              );
            })}
          </div>
          <div className="flex justify-between px-1 mt-1">
            {dayLabels.map((d, i) => (
              <span key={i} className="flex-1 text-center text-[9px] font-medium text-[color:var(--purch-muted-ink)]">
                {d}
              </span>
            ))}
          </div>
        </>
      ) : (
        <p className="text-[12px] text-[color:var(--purch-muted-ink)] m-0 py-4 text-center">
          No spending yet — try &quot;coffee 150&quot; in chat.
        </p>
      )}
    </div>
  );
}
