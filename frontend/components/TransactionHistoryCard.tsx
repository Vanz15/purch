"use client";

import { useEffect, useState, useMemo } from "react";
import { api, TransactionRow } from "@/lib/api";
import { Search } from "lucide-react";

const CATEGORY_COLORS: Record<string, { bg: string; text: string }> = {
  Food:          { bg: "#DBEAFE", text: "#1D4ED8" },
  Transport:     { bg: "#FEF3C7", text: "#B45309" },
  Shopping:      { bg: "#FCE7F3", text: "#BE185D" },
  Entertainment: { bg: "#EDE9FE", text: "#6D28D9" },
  Bills:         { bg: "#FEE2E2", text: "#B91C1C" },
  Health:        { bg: "#D1FAE5", text: "#047857" },
  Education:     { bg: "#E0F2FE", text: "#0369A1" },
  Income:        { bg: "#D1FAE5", text: "#047857" },
};

function categoryColor(cat: string) {
  return CATEGORY_COLORS[cat] ?? { bg: "#F1F5F9", text: "#475569" };
}

function groupByDay(txs: TransactionRow[]): Map<string, TransactionRow[]> {
  const groups = new Map<string, TransactionRow[]>();
  for (const t of txs) {
    const raw = t.tx_timestamp ?? "";
    const dateStr = raw.split("T")[0].split(" ")[0] ?? "Unknown";
    const arr = groups.get(dateStr) ?? [];
    arr.push(t);
    groups.set(dateStr, arr);
  }
  return groups;
}

function dayLabel(dateStr: string): string {
  const today = new Date();
  const d = new Date(dateStr + "T00:00:00");
  if (isNaN(d.getTime())) return dateStr;
  const diff = Math.floor((today.getTime() - d.getTime()) / 86400000);
  if (diff === 0) return "Today";
  if (diff === 1) return "Yesterday";
  return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
}

export function TransactionHistoryCard() {
  const [txs, setTxs] = useState<TransactionRow[]>([]);
  const [search, setSearch] = useState("");
  const [catFilter, setCatFilter] = useState("");

  async function load() {
    try {
      const data = await api.transactions.list({ limit: 50 });
      setTxs(data.transactions || []);
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

  // Get unique categories for filter
  const categories = useMemo(() => {
    const cats = new Set(txs.map((t) => t.category).filter(Boolean));
    return Array.from(cats).sort();
  }, [txs]);

  // Filter transactions
  const filtered = useMemo(() => {
    return txs.filter((t) => {
      if (catFilter && t.category !== catFilter) return false;
      if (search.trim()) {
        const q = search.toLowerCase();
        if (!t.item?.toLowerCase().includes(q) && !t.category?.toLowerCase().includes(q)) return false;
      }
      return true;
    });
  }, [txs, search, catFilter]);

  const grouped = groupByDay(filtered);

  return (
    <div
      className="rounded-2xl p-5 flex flex-col"
      style={{ background: "var(--purch-paper)", boxShadow: "var(--purch-shadow-md)", border: "1px solid var(--purch-line)" }}
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-sans font-bold text-[20px] m-0">Transaction History</h3>
        <span className="text-[11px] text-[color:var(--purch-taupe)]">{filtered.length} of {txs.length}</span>
      </div>

      {/* Search + filter row */}
      <div className="flex items-center gap-2 mb-3">
        <div className="relative flex-1">
          <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[color:var(--purch-muted-ink)]" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search…"
            className="w-full h-8 rounded-lg pl-8 pr-2 text-[12px] bg-[color:var(--purch-bg)]"
            style={{ border: "1px solid var(--purch-line-soft)", color: "var(--purch-ink)" }}
          />
        </div>
        <select
          value={catFilter}
          onChange={(e) => setCatFilter(e.target.value)}
          className="h-8 rounded-lg px-2 text-[11px] font-semibold bg-[color:var(--purch-bg)]"
          style={{ border: "1px solid var(--purch-line-soft)", color: "var(--purch-ink)" }}
        >
          <option value="">All</option>
          {categories.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      {filtered.length === 0 ? (
        <p className="text-[12px] text-[color:var(--purch-muted-ink)] m-0 py-4 text-center">
          No transactions yet — try &quot;milk tea 85 Gcash&quot; in chat.
        </p>
      ) : (
        /* Fixed height scrollable area — shows ~5 rows then scrolls */
        <div className="overflow-y-auto" style={{ maxHeight: 280 }}>
          {Array.from(grouped.entries()).map(([dateStr, rows]) => {
            const dayTotal = rows.reduce((s, t) => s + (t.amount ?? 0), 0);
            return (
              <div key={dateStr}>
                <div
                  className="flex items-center justify-between py-1.5 px-1 border-b sticky top-0 bg-[color:var(--purch-paper)]"
                  style={{ borderColor: "var(--purch-line-soft)" }}
                >
                  <span className="text-[13px] font-semibold" style={{ color: "var(--purch-ink)" }}>
                    {dayLabel(dateStr)}
                  </span>
                  <div className="flex items-center gap-3">
                    <span className="font-['JetBrains_Mono'] text-[10.5px] text-[color:var(--purch-muted-ink)]">
                      {dayTotal >= 0 ? "-" : "+"}₱{Math.abs(dayTotal).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </span>
                    <span className="text-[10px] text-[color:var(--purch-muted-ink)]">
                      {rows.length} txn{rows.length !== 1 ? "s" : ""}
                    </span>
                  </div>
                </div>

                {rows.map((t, i) => {
                  const cc = categoryColor(t.category);
                  const isNeg = (t.amount ?? 0) < 0;
                  return (
                    <div
                      key={t.transaction_id ?? i}
                      className="flex items-center justify-between py-2 px-1 border-b last:border-0"
                      style={{ borderColor: "var(--purch-line-soft)" }}
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <div
                          className="w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0"
                          style={{ background: cc.bg, color: cc.text }}
                        >
                          {t.category?.charAt(0)?.toUpperCase() ?? "?"}
                        </div>
                        <div className="min-w-0">
                          <div className="text-[14px] font-medium truncate">{t.item || "—"}</div>
                          <div className="flex items-center gap-1.5 mt-0.5">
                            <span
                              className="text-[12px] px-1.5 py-0.5 rounded font-medium"
                              style={{ background: cc.bg, color: cc.text }}
                            >
                              {t.category || "Uncategorized"}
                            </span>
                            {t.wallet && (
                              <span className="text-[9px] text-[color:var(--purch-muted-ink)]">
                                {t.wallet}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                      <span
                        className="font-['JetBrains_Mono'] text-[14px] font-semibold shrink-0 ml-2"
                        style={{ color: isNeg ? "var(--purch-coral)" : "var(--purch-teal)" }}
                      >
                        {t.amount_display || `₱${(t.amount ?? 0).toFixed(2)}`}
                      </span>
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
