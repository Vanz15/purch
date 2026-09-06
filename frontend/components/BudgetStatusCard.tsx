"use client";

import { useEffect, useState } from "react";
import { api, BudgetStatusRow } from "@/lib/api";

export function BudgetStatusCard() {
  const [budgets, setBudgets] = useState<BudgetStatusRow[]>([]);

  async function load() {
    try {
      const a = await api.analytics.get(0, 0);
      setBudgets(a.budgets ?? []);
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

  return (
    <div
      className="rounded-2xl p-5 flex flex-col"
      style={{ background: "var(--purch-paper)", boxShadow: "var(--purch-shadow-md)", border: "1px solid var(--purch-line)" }}
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-sans font-bold text-[20px] m-0">Budget Status</h3>
      </div>

      {budgets.length === 0 ? (
        <p className="text-[14px] text-[color:var(--purch-muted-ink)] m-0">
          No budgets set yet — try &quot;set food budget to 3000&quot; in chat.
        </p>
      ) : (
        /* Scrollable if content exceeds height */
        <div className="overflow-y-auto flex-1" style={{ maxHeight: 200 }}>
          <div className="flex flex-col gap-3">
            {budgets.map((b) => {
              const color =
                b.status === "over" ? "var(--purch-coral)" : b.status === "near" ? "var(--purch-gold)" : "var(--purch-teal)";
              return (
                <div key={b.category}>
                  <div className="flex justify-between text-[14px] mb-1">
                    <span className="font-medium">{b.category}</span>
                    <span style={{ color }}>
                      ₱{b.spent.toLocaleString()} / ₱{b.limit_amount.toLocaleString()}
                    </span>
                  </div>
                  <div className="h-1.5 rounded-full" style={{ background: "var(--purch-line)" }}>
                    <div className="h-full rounded-full" style={{ width: `${b.pct ?? 0}%`, background: color }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
