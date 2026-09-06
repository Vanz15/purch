"use client";

import { useEffect, useState } from "react";
import { api, WalletRow } from "@/lib/api";
import { Landmark, PiggyBank, Wallet, Banknote } from "lucide-react";

const WALLET_PALETTE = [
  { bg: "#B8860B", text: "#FFFFFF" },  // Dark Gold
  { bg: "#0D1B4C", text: "#FFFFFF" },  // Navy
  { bg: "#7A1F2B", text: "#FFFFFF" },  // Crimson
  { bg: "#2F4F3F", text: "#FFFFFF" },  // Dark Green
  { bg: "#4A2C5E", text: "#FFFFFF" },  // Deep Purple
  { bg: "#1F5C5C", text: "#FFFFFF" },  // Teal
  { bg: "#5C3A1E", text: "#FFFFFF" },  // Brown
  { bg: "#3E3E3E", text: "#FFFFFF" },  // Charcoal
  { bg: "#1E4620", text: "#FFFFFF" },  // Forest
  { bg: "#6B2F5F", text: "#FFFFFF" },  // Magenta
];

const WALLET_TYPE_COLOR: Record<string, number> = {
  Cash: 0, Bank: 1, Savings: 2, "E-wallet": 3,
  Investment: 4, Lent: 5, Borrowed: 6, Debt: 7,
};

function walletColor(type: string, idx: number) {
  const mapIdx = WALLET_TYPE_COLOR[type];
  if (mapIdx != null) return WALLET_PALETTE[mapIdx];
  return WALLET_PALETTE[idx % WALLET_PALETTE.length];
}

function walletIcon(type: string) {
  switch (type) {
    case "Cash": return Banknote;
    case "Bank": return Landmark;
    case "Savings": return PiggyBank;
    default: return Wallet;
  }
}

const FAV_KEY = "purch:favorites";

export function loadFavorites(): Set<number> {
  try {
    const raw = localStorage.getItem(FAV_KEY);
    return raw ? new Set(JSON.parse(raw)) : new Set();
  } catch {
    return new Set();
  }
}

export function saveFavorites(ids: Set<number>) {
  try {
    localStorage.setItem(FAV_KEY, JSON.stringify([...ids]));
  } catch { /* ignore */ }
}

export function toggleFavorite(id: number) {
  const favs = loadFavorites();
  if (favs.has(id)) favs.delete(id);
  else favs.add(id);
  saveFavorites(favs);
}

export function WalletStack() {
  const [wallets, setWallets] = useState<WalletRow[]>([]);
  const favorites = loadFavorites();

  async function load() {
    try {
      const w = await api.wallets.list(true);
      setWallets((w.wallets || []).filter((x: WalletRow) => !x.is_archived));
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

  // Sort: favorites first, then by wallet list order
  const sorted = [...wallets].sort((a, b) => {
    const af = favorites.has(a.id) ? 0 : 1;
    const bf = favorites.has(b.id) ? 0 : 1;
    return af - bf;
  });

  const hasFavs = sorted.some((w) => favorites.has(w.id));
  const displayWallets = hasFavs
    ? sorted.filter((w) => favorites.has(w.id)).slice(0, 3)
    : sorted.slice(0, 3);

  const total = wallets.reduce((sum, w) => sum + (w.balance ?? 0), 0);

  const CARD_H = 56;
  // Overlap between consecutive wallet cards — small enough to show each card's name + balance
  const CARD_OVERLAP = 14;
  const LAST_TO_SUMMARY_OVERLAP = 10; // between front card and white summary card

  // Concave clip-path for the white card: smooth scoop at top center
  const CLIP_PATH = `polygon(` +
    `0% 0%, ` +
    `calc(50% - 40px) 0%, ` +
    `calc(50% - 36px) 1px, ` +
    `calc(50% - 30px) 3px, ` +
    `calc(50% - 22px) 7px, ` +
    `calc(50% - 14px) 11px, ` +
    `calc(50% - 6px) 13px, ` +
    `calc(50%) 14px, ` +
    `calc(50% + 6px) 13px, ` +
    `calc(50% + 14px) 11px, ` +
    `calc(50% + 22px) 7px, ` +
    `calc(50% + 30px) 3px, ` +
    `calc(50% + 36px) 1px, ` +
    `calc(50% + 40px) 0%, ` +
    `100% 0%, ` +
    `100% 100%, ` +
    `0% 100%)`;

  return (
    <div className="flex flex-col">
      {/* Wallet cards — newest/favorite on top, cascading down */}
      <div className="flex flex-col">
        {displayWallets.map((w, i) => {
          const paletteColor = walletColor(w.wallet_type, wallets.indexOf(w));
          const color = w.color
            ? { bg: w.color, text: "#FFFFFF" }
            : paletteColor;
          const isLast = i === displayWallets.length - 1;
          const Icon = walletIcon(w.wallet_type);

          // Each card overlaps the one behind by CARD_OVERLAP (14px),
          // showing 42px of each card's content — enough for name + balance.
          const overlap = i === 0 ? 0 : CARD_OVERLAP;

          return (
            <div
              key={w.id}
              className={`px-4 py-3 flex items-center justify-between rounded-t-2xl ${isLast ? "rounded-b-2xl" : "rounded-b-none"}`}
              style={{
                height: CARD_H,
                marginTop: i > 0 ? -overlap : 0,
                background: color.bg,
                color: color.text,
                boxShadow: "0 4px 16px rgba(0,0,0,0.15)",
                position: "relative",
              }}
            >
              <div className="flex items-center gap-2.5">
                <Icon size={15} />
                <span className="text-[13px] font-semibold uppercase tracking-wide">
                  {w.name}
                </span>
              </div>
              <span className="text-[15px] font-bold" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                <span style={{ fontFamily: "inherit" }}>₱</span>{w.balance_display}
              </span>
            </div>
          );
        })}
      </div>

      {/* Summary card — total balance, sits at bottom.
          Uses filter: drop-shadow instead of box-shadow so the shadow
          follows the clip-path concave notch cleanly. */}
      <div
        className="relative rounded-2xl px-5 py-6 flex items-end justify-between"
        style={{
          background: "#FFFFFF",
          filter: "drop-shadow(0 2px 4px rgba(0,0,0,0.06)) drop-shadow(0 6px 16px rgba(0,0,0,0.07))",
          marginTop: -LAST_TO_SUMMARY_OVERLAP,
          zIndex: 0,
          clipPath: CLIP_PATH,
        }}
      >
        {/* Add wallet button — top right */}
        <a
          href="/wallets"
          className="absolute top-2 right-3 z-10 w-6 h-6 rounded-full flex items-center justify-center text-[13px] font-semibold transition-opacity hover:opacity-70"
          style={{
            background: "var(--purch-paper)",
            color: "var(--purch-muted-ink)",
            boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
          }}
          title="Add a wallet"
        >
          +
        </a>

        <div>
          <div className="text-[11px] uppercase tracking-[0.08em] text-[color:var(--purch-taupe)] mb-1">
            {wallets.length} card{wallets.length !== 1 ? "s" : ""}
          </div>
          <div className="text-[10.5px] text-[color:var(--purch-muted-ink)]">
            Wallet Balance
          </div>
        </div>
        <span className="text-[26px] font-bold" style={{ fontFamily: "'JetBrains Mono', monospace", color: "var(--purch-ink)" }}>
          <span style={{ fontFamily: "inherit" }}>₱</span>{total.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </span>
      </div>
    </div>
  );
}
