"""Analytics page sections — KPIs, category breakdown, trend, budget
status, and recent transactions. Kept in a dedicated component module
so `pages/analytics.py` stays focused on layout composition."""

from __future__ import annotations

import reflex as rx

from purch.states.analytics_state import (
    AnalyticsState,
    BudgetStatusRow,
    CategoryRow,
    RecentTx,
    TrendPoint,
    WalletBar,
)
from purch.theme import CLASSES, ROUTES

# ---------------------------------------------------------------------- #
# Small primitives
# ---------------------------------------------------------------------- #


def _skeleton_line(width: str = "w-24") -> rx.Component:
    return rx.el.div(
        class_name=(
            f"h-3 rounded-full bg-[color:var(--purch-border)]/60 "
            f"animate-pulse {width}"
        ),
    )


def _section_heading(eyebrow: str, title: str, *right) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(eyebrow, class_name=CLASSES["eyebrow"]),
            rx.el.h2(
                title,
                class_name=(
                    "font-['Playfair_Display'] font-bold text-xl sm:text-2xl "
                    "text-[color:var(--purch-ink)] mt-1"
                ),
            ),
            class_name="flex-1 min-w-0",
        ),
        rx.el.div(*right, class_name="flex items-center gap-2"),
        class_name="flex items-end justify-between gap-3 mb-4",
    )


def _empty_note(text: str) -> rx.Component:
    return rx.el.div(
        text,
        class_name=(
            "text-sm text-[color:var(--purch-muted)] italic py-8 text-center"
        ),
    )


# ---------------------------------------------------------------------- #
# KPI row
# ---------------------------------------------------------------------- #


def _kpi_card(
    eyebrow: str,
    value: rx.Component,
    hint: rx.Component | str,
    tone: str = "default",
) -> rx.Component:
    return rx.el.div(
        rx.el.div(eyebrow, class_name=CLASSES["eyebrow"]),
        rx.el.div(
            value,
            class_name=rx.cond(
                tone == "coral",
                "font-['Playfair_Display'] font-bold text-3xl mt-2 text-[color:var(--purch-coral)]",
                rx.cond(
                    tone == "gold",
                    "font-['Playfair_Display'] font-bold text-3xl mt-2 text-[color:var(--purch-gold)]",
                    rx.cond(
                        tone == "danger",
                        "font-['Playfair_Display'] font-bold text-3xl mt-2 text-[color:var(--purch-danger)]",
                        "font-['Playfair_Display'] font-bold text-3xl mt-2 text-[color:var(--purch-ink)]",
                    ),
                ),
            ),
        ),
        rx.el.div(
            hint,
            class_name="text-xs text-[color:var(--purch-muted)] mt-2 leading-relaxed",
        ),
        class_name=f"{CLASSES['card']} p-5 w-full h-full flex flex-col",
    )


def _kpi_row() -> rx.Component:
    return rx.el.div(
        _kpi_card(
            "This month spent",
            rx.el.span(
                rx.el.span(
                    "₱",
                    class_name="text-xl text-[color:var(--purch-muted)] mr-0.5",
                ),
                AnalyticsState.month_spent.to_string(),
            ),
            rx.cond(
                AnalyticsState.month_tx_count > 0,
                rx.el.span(
                    "Across ",
                    AnalyticsState.month_tx_count.to_string(),
                    " transactions",
                ),
                rx.el.span("No transactions yet this month"),
            ),
            tone="coral",
        ),
        _kpi_card(
            "Transactions",
            AnalyticsState.month_tx_count.to_string(),
            rx.el.span("Logged this month"),
        ),
        _kpi_card(
            "Top category",
            AnalyticsState.top_category,
            rx.cond(
                AnalyticsState.top_category_amount > 0,
                rx.el.span(
                    "₱",
                    AnalyticsState.top_category_amount.to_string(),
                    " this month",
                ),
                rx.el.span("—"),
            ),
            tone="gold",
        ),
        _kpi_card(
            "Budget used",
            rx.el.span(AnalyticsState.budget_used_pct.to_string(), "%"),
            rx.cond(
                AnalyticsState.budget_limit_total > 0,
                rx.el.span(
                    "₱",
                    AnalyticsState.budget_spent_total.to_string(),
                    " of ₱",
                    AnalyticsState.budget_limit_total.to_string(),
                ),
                rx.el.span("Set a budget in chat to track this"),
            ),
            tone=rx.cond(
                AnalyticsState.budget_used_pct >= 100,
                "danger",
                rx.cond(
                    AnalyticsState.budget_used_pct >= 80, "gold", "default"
                ),
            ),
        ),
        _kpi_card(
            "Spendable now",
            rx.el.span(
                rx.el.span(
                    "\u20b1",
                    class_name="text-xl text-[color:var(--purch-muted)] mr-0.5",
                ),
                AnalyticsState.wallet_assets_display,
            ),
            rx.cond(
                AnalyticsState.wallets_unavailable,
                rx.el.span("Wallets need the cloud database"),
                rx.cond(
                    AnalyticsState.has_wallet_liabilities,
                    rx.el.span(
                        "\u20b1",
                        AnalyticsState.wallet_liabilities_display,
                        " owed / lent out",
                    ),
                    rx.cond(
                        AnalyticsState.has_wallets,
                        rx.el.span("Across your active wallets"),
                        rx.el.span("Add a wallet to track balances"),
                    ),
                ),
            ),
            tone="gold",
        ),
        class_name=(
            "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 w-full"
        ),
    )


# ---------------------------------------------------------------------- #
# Wallet / bank status
# ---------------------------------------------------------------------- #


def _wallet_totals() -> rx.Component:
    """Net worth hero + assets / liabilities tiles."""

    def tile(label: str, value: rx.Var, tone: str) -> rx.Component:
        return rx.el.div(
            rx.el.div(label, class_name=CLASSES["eyebrow"]),
            rx.el.div(
                rx.el.span(
                    "\u20b1",
                    class_name="text-base text-[color:var(--purch-muted)] mr-0.5",
                ),
                rx.el.span(value),
                class_name=(
                    "font-['DM_Mono'] font-bold text-xl mt-1.5 "
                    + {
                        "teal": "text-[color:var(--purch-teal)]",
                        "danger": "text-[color:var(--purch-danger)]",
                        "gold": "text-[color:var(--purch-gold)]",
                    }.get(tone, "text-[color:var(--purch-ink)]")
                ),
            ),
            class_name=(
                "rounded-xl border border-[color:var(--purch-border)] "
                "bg-[color:var(--purch-parchment)] p-4 w-full"
            ),
        )

    return rx.el.div(
        rx.el.div(
            rx.el.div(
                "Net worth",
                class_name=(
                    "font-['DM_Mono'] text-[0.65rem] uppercase "
                    "tracking-[0.12em] text-[color:var(--purch-gold)]"
                ),
            ),
            rx.el.div(
                rx.el.span(
                    "\u20b1",
                    class_name=(
                        "font-['DM_Mono'] text-2xl "
                        "text-[color:var(--purch-parchment)]/70 mr-1"
                    ),
                ),
                rx.el.span(
                    AnalyticsState.wallet_net_display,
                    class_name=(
                        "font-['Playfair_Display'] font-bold text-4xl "
                        "text-[color:var(--purch-parchment)]"
                    ),
                ),
                class_name="flex items-baseline mt-2",
            ),
            rx.el.p(
                "Assets minus everything you owe.",
                class_name=("text-xs text-[color:var(--purch-muted)] mt-2 m-0"),
            ),
            class_name=(
                "bg-[color:var(--purch-dark)] rounded-xl p-5 mb-3 w-full"
            ),
        ),
        rx.el.div(
            tile("Assets", AnalyticsState.wallet_assets_display, "teal"),
            tile(
                "Liabilities",
                AnalyticsState.wallet_liabilities_display,
                "danger",
            ),
            class_name="grid grid-cols-1 sm:grid-cols-2 gap-3",
        ),
        class_name="mb-5",
    )


def _wallet_group_block(
    label: str,
    subtitle: str,
    total_display: rx.Var,
    insight: rx.Var,
    bars: rx.Var,
    has_bars: rx.Var,
    tone: str,
) -> rx.Component:
    amount_class = "font-['DM_Mono'] text-lg font-bold " + {
        "teal": "text-[color:var(--purch-teal)]",
        "gold": "text-[color:var(--purch-gold)]",
        "danger": "text-[color:var(--purch-danger)]",
    }.get(tone, "text-[color:var(--purch-ink)]")
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.h3(
                    label,
                    class_name=(
                        "font-['Playfair_Display'] font-bold text-base "
                        "text-[color:var(--purch-ink)] m-0"
                    ),
                ),
                rx.el.p(
                    subtitle,
                    class_name=f"{CLASSES['eyebrow']} mt-0.5 m-0",
                ),
                class_name="flex-1 min-w-0",
            ),
            rx.el.span(
                rx.el.span("\u20b1", total_display),
                class_name=amount_class,
            ),
            class_name="flex items-start justify-between gap-3",
        ),
        rx.el.p(
            insight,
            class_name=(
                "text-xs text-[color:var(--purch-muted)] mt-1.5 mb-3 "
                "leading-relaxed m-0"
            ),
        ),
        rx.cond(
            has_bars,
            rx.el.div(rx.foreach(bars, _wallet_bar)),
            rx.fragment(),
        ),
        class_name=(
            "rounded-xl border border-[color:var(--purch-border)] "
            "bg-[color:var(--purch-parchment)] p-4 w-full"
        ),
    )


def _wallet_groups() -> rx.Component:
    return rx.el.div(
        _wallet_group_block(
            "Debit",
            "Bank · Cash · Savings",
            AnalyticsState.debit_total_display,
            AnalyticsState.debit_insight,
            AnalyticsState.debit_bars,
            AnalyticsState.has_debit_wallets,
            "teal",
        ),
        _wallet_group_block(
            "Lent",
            "Money you're waiting on",
            AnalyticsState.lent_total_display,
            AnalyticsState.lent_insight,
            AnalyticsState.lent_bars,
            AnalyticsState.has_lent_wallets,
            "gold",
        ),
        _wallet_group_block(
            "Borrowed",
            "Debt · Loan",
            AnalyticsState.borrowed_total_display,
            AnalyticsState.borrowed_insight,
            AnalyticsState.borrowed_bars,
            AnalyticsState.has_borrowed_wallets,
            "danger",
        ),
        class_name="grid grid-cols-1 lg:grid-cols-3 gap-3",
    )


def _wallet_bar(wallet: WalletBar) -> rx.Component:
    fill_class = rx.match(
        wallet["accent"],
        (
            "gold",
            "h-full rounded-full bg-gradient-to-r "
            "from-[color:var(--purch-gold)] to-[color:var(--purch-coral-light)]",
        ),
        (
            "teal",
            "h-full rounded-full bg-gradient-to-r "
            "from-[color:var(--purch-teal)] to-[color:var(--purch-gold)]",
        ),
        ("danger", "h-full rounded-full bg-[color:var(--purch-danger)]"),
        "h-full rounded-full bg-[color:var(--purch-muted)]",
    )
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.span(
                    wallet["name"],
                    class_name=(
                        "text-sm font-semibold text-[color:var(--purch-ink)] "
                        "truncate"
                    ),
                ),
                _type_pill(wallet["wallet_type"], wallet["accent"]),
                class_name="flex items-center gap-2 min-w-0",
            ),
            rx.el.span(
                rx.el.span("\u20b1", wallet["balance_display"]),
                class_name=rx.cond(
                    wallet["is_liability"],
                    "font-['DM_Mono'] text-sm font-bold "
                    "text-[color:var(--purch-danger)] shrink-0",
                    "font-['DM_Mono'] text-sm font-bold "
                    "text-[color:var(--purch-ink)] shrink-0",
                ),
            ),
            class_name="flex items-center justify-between gap-3 mb-1.5",
        ),
        rx.el.div(
            rx.el.div(
                class_name=fill_class,
                style={"width": wallet["pct"].to_string() + "%"},
            ),
            class_name=(
                "h-2.5 rounded-full bg-[color:var(--purch-border)] "
                "overflow-hidden"
            ),
        ),
        rx.el.div(
            rx.el.span(
                wallet["movement_display"],
                class_name=(
                    "font-['DM_Mono'] text-[0.65rem] "
                    "text-[color:var(--purch-muted)]"
                ),
            ),
            rx.cond(
                wallet["movement_count"] > 0,
                rx.el.span(
                    wallet["movement_count"].to_string(),
                    " movements",
                    class_name=(
                        "font-['DM_Mono'] text-[0.65rem] "
                        "text-[color:var(--purch-muted)]"
                    ),
                ),
                rx.fragment(),
            ),
            class_name="flex items-center justify-between mt-1",
        ),
        class_name="mb-4 last:mb-0",
    )


def _type_pill(wallet_type: rx.Var, accent: rx.Var) -> rx.Component:
    return rx.el.span(
        wallet_type,
        class_name=rx.match(
            accent,
            (
                "gold",
                "inline-flex items-center rounded-full px-2 py-0.5 "
                "font-['DM_Mono'] text-[0.55rem] uppercase tracking-[0.1em] "
                "bg-[color:var(--purch-gold)]/15 text-[color:var(--purch-gold)] "
                "shrink-0",
            ),
            (
                "teal",
                "inline-flex items-center rounded-full px-2 py-0.5 "
                "font-['DM_Mono'] text-[0.55rem] uppercase tracking-[0.1em] "
                "bg-[color:var(--purch-teal)]/15 text-[color:var(--purch-teal)] "
                "shrink-0",
            ),
            (
                "danger",
                "inline-flex items-center rounded-full px-2 py-0.5 "
                "font-['DM_Mono'] text-[0.55rem] uppercase tracking-[0.1em] "
                "bg-[color:var(--purch-danger)]/10 "
                "text-[color:var(--purch-danger)] shrink-0",
            ),
            "inline-flex items-center rounded-full px-2 py-0.5 "
            "font-['DM_Mono'] text-[0.55rem] uppercase tracking-[0.1em] "
            "bg-[color:var(--purch-parchment)] "
            "text-[color:var(--purch-muted)] shrink-0",
        ),
    )


def _wallet_detail_row(wallet: WalletBar) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.p(
                wallet["name"],
                class_name=(
                    "text-sm font-semibold text-[color:var(--purch-ink)] "
                    "m-0 truncate leading-tight"
                ),
            ),
            rx.el.p(
                _type_pill(wallet["wallet_type"], wallet["accent"]),
                rx.cond(
                    wallet["note"] != "",
                    rx.el.span(
                        wallet["note"],
                        class_name=(
                            "text-[0.7rem] text-[color:var(--purch-muted)] ml-2"
                        ),
                    ),
                    rx.fragment(),
                ),
                class_name="mt-1 m-0 flex items-center min-w-0",
            ),
            class_name="flex-1 min-w-0",
        ),
        rx.el.div(
            rx.el.span(
                rx.el.span("\u20b1", wallet["balance_display"]),
                class_name=rx.cond(
                    wallet["is_liability"],
                    "font-['DM_Mono'] text-sm font-bold "
                    "text-[color:var(--purch-danger)]",
                    "font-['DM_Mono'] text-sm font-bold "
                    "text-[color:var(--purch-teal)]",
                ),
            ),
            class_name="ml-3 shrink-0 text-right",
        ),
        class_name=(
            "flex items-start justify-between py-3 "
            "border-b border-dashed border-[color:var(--purch-border)] "
            "last:border-b-0"
        ),
    )


def _wallet_section() -> rx.Component:
    return rx.el.section(
        _section_heading(
            "Wallet & bank status",
            "Where your money sits",
            rx.el.a(
                "Manage wallets \u2192",
                href=ROUTES["wallets"],
                class_name=(
                    "text-xs font-semibold text-[color:var(--purch-coral)] "
                    "hover:text-[color:var(--purch-coral-light)] "
                    "transition-colors"
                ),
            ),
        ),
        rx.cond(
            AnalyticsState.wallets_unavailable,
            _empty_note(
                "Wallet balances need the cloud database \u2014 spending "
                "analytics above still works."
            ),
            rx.cond(
                AnalyticsState.has_wallets,
                rx.el.div(
                    _wallet_totals(),
                    _wallet_groups(),
                    rx.el.div(
                        rx.el.div(
                            "Wallet details",
                            class_name=f"{CLASSES['eyebrow']} mb-1",
                        ),
                        rx.foreach(
                            AnalyticsState.wallet_bars, _wallet_detail_row
                        ),
                        class_name="mt-5",
                    ),
                ),
                rx.el.div(
                    rx.el.p(
                        "No wallets yet.",
                        class_name=(
                            "font-['Playfair_Display'] font-bold text-lg "
                            "text-[color:var(--purch-ink)] mb-1"
                        ),
                    ),
                    rx.el.p(
                        "Add cash, bank, savings, debt, or lent-out wallets "
                        "and their status will appear here beside your spending.",
                        class_name="text-sm text-[color:var(--purch-muted)]",
                    ),
                    rx.el.a(
                        "Add a wallet",
                        href=ROUTES["wallets"],
                        class_name=CLASSES["primary_button"] + " mt-4 text-sm",
                    ),
                    class_name="py-8 text-center flex flex-col items-center",
                ),
            ),
        ),
        class_name=f"{CLASSES['card']} p-6",
    )


# ---------------------------------------------------------------------- #
# Category breakdown
# ---------------------------------------------------------------------- #


def _category_row(row: CategoryRow) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.span(
                row["category"],
                class_name="text-sm font-semibold text-[color:var(--purch-ink)]",
            ),
            rx.el.span(
                rx.el.span(
                    row["count"].to_string(),
                    " tx",
                    class_name=(
                        "font-['DM_Mono'] text-[0.65rem] "
                        "text-[color:var(--purch-muted)] ml-2"
                    ),
                ),
                rx.el.span(
                    rx.el.span("₱", row["total"].to_string()),
                    class_name=(
                        "font-['DM_Mono'] text-sm font-semibold "
                        "text-[color:var(--purch-coral)] ml-3"
                    ),
                ),
                class_name="flex items-baseline",
            ),
            class_name="flex items-center justify-between mb-1.5",
        ),
        rx.el.div(
            rx.el.div(
                class_name=(
                    "h-full rounded-full bg-gradient-to-r "
                    "from-[color:var(--purch-coral)] to-[color:var(--purch-coral-light)]"
                ),
                style={
                    "width": rx.cond(
                        row["pct_of_total"] > 100,
                        "100%",
                        row["pct_of_total"].to_string() + "%",
                    )
                },
            ),
            class_name=(
                "h-2 rounded-full bg-[color:var(--purch-border)] overflow-hidden"
            ),
        ),
        rx.el.div(
            rx.el.span(
                row["pct_of_total"].to_string(),
                "% of monthly spend",
                class_name=(
                    "font-['DM_Mono'] text-[0.65rem] text-[color:var(--purch-muted)]"
                ),
            ),
            class_name="mt-1",
        ),
        class_name="mb-4 last:mb-0",
    )


def _category_section() -> rx.Component:
    return rx.el.section(
        _section_heading(
            "Where it went",
            "Category breakdown",
            rx.el.span(
                AnalyticsState.month_label,
                class_name="text-xs text-[color:var(--purch-muted)]",
            ),
        ),
        rx.cond(
            AnalyticsState.has_categories,
            rx.el.div(rx.foreach(AnalyticsState.category_rows, _category_row)),
            _empty_note(
                "No spending logged this month yet — try 'coffee 150' in chat."
            ),
        ),
        class_name=f"{CLASSES['card']} p-6",
    )


# ---------------------------------------------------------------------- #
# Trend
# ---------------------------------------------------------------------- #


def _trend_bar(point: TrendPoint, index: rx.Var) -> rx.Component:
    """One vertical bar in the sparkline. Height is scaled against
    `trend_peak` so the tallest day is always ~100%. Zero-days render
    as a thin baseline so the axis feels continuous."""
    ratio = rx.cond(
        AnalyticsState.trend_peak > 0,
        (point["total"] * 100) / AnalyticsState.trend_peak,
        0,
    )
    return rx.el.div(
        rx.el.div(
            class_name=rx.cond(
                point["total"] > 0,
                "w-full rounded-t-md bg-[color:var(--purch-coral)] transition-all",
                "w-full rounded-t-md bg-[color:var(--purch-border)]",
            ),
            style={
                "height": rx.cond(
                    point["total"] > 0,
                    f"calc({ratio}% + 4px)",
                    "3px",
                )
            },
            title=f"{point['day']} · ₱{point['total']} · {point['count']} tx",
        ),
        class_name="flex flex-col justify-end h-full flex-1 min-w-0 px-[1px]",
    )


def _trend_section() -> rx.Component:
    return rx.el.section(
        _section_heading(
            "Last 30 days",
            "Spending trend",
            rx.cond(
                AnalyticsState.trend_peak > 0,
                rx.el.span(
                    "Peak day: ₱",
                    AnalyticsState.trend_peak.to_string(),
                    class_name=(
                        "font-['DM_Mono'] text-[0.65rem] "
                        "text-[color:var(--purch-muted)]"
                    ),
                ),
                rx.fragment(),
            ),
        ),
        rx.cond(
            AnalyticsState.has_trend_data,
            rx.el.div(
                rx.el.div(
                    rx.foreach(AnalyticsState.trend_points, _trend_bar),
                    class_name="flex items-end w-full h-40 gap-0.5",
                ),
                rx.el.div(
                    rx.el.span(
                        AnalyticsState.trend_points[0]["day"],
                        class_name=(
                            "font-['DM_Mono'] text-[0.6rem] "
                            "text-[color:var(--purch-muted)]"
                        ),
                    ),
                    rx.el.span(
                        AnalyticsState.trend_points[
                            AnalyticsState.trend_points.length() - 1
                        ]["day"],
                        class_name=(
                            "font-['DM_Mono'] text-[0.6rem] "
                            "text-[color:var(--purch-muted)]"
                        ),
                    ),
                    class_name=(
                        "flex items-center justify-between mt-2 "
                        "pt-2 border-t border-dashed border-[color:var(--purch-border)]"
                    ),
                ),
            ),
            _empty_note(
                "No activity in the last 30 days — log a purchase to see the trend."
            ),
        ),
        class_name=f"{CLASSES['card']} p-6",
    )


# ---------------------------------------------------------------------- #
# Budget status
# ---------------------------------------------------------------------- #


def _status_pill(status: rx.Var) -> rx.Component:
    return rx.match(
        status,
        (
            "over",
            rx.el.span(
                "Over budget",
                class_name=(
                    "inline-flex items-center rounded-full px-2 py-0.5 "
                    "text-[0.6rem] font-bold uppercase tracking-wider "
                    "bg-[color:var(--purch-danger)]/10 text-[color:var(--purch-danger)]"
                ),
            ),
        ),
        (
            "near",
            rx.el.span(
                "Almost there",
                class_name=(
                    "inline-flex items-center rounded-full px-2 py-0.5 "
                    "text-[0.6rem] font-bold uppercase tracking-wider "
                    "bg-[color:var(--purch-gold)]/15 text-[color:var(--purch-gold)]"
                ),
            ),
        ),
        rx.el.span(
            "On track",
            class_name=(
                "inline-flex items-center rounded-full px-2 py-0.5 "
                "text-[0.6rem] font-bold uppercase tracking-wider "
                "bg-[color:var(--purch-teal)]/15 text-[color:var(--purch-teal)]"
            ),
        ),
    )


def _budget_card(row: BudgetStatusRow) -> rx.Component:
    fill_class = rx.match(
        row["status"],
        ("over", "bg-[color:var(--purch-danger)] h-full rounded-full"),
        ("near", "bg-[color:var(--purch-gold)] h-full rounded-full"),
        "bg-[color:var(--purch-coral)] h-full rounded-full",
    )
    return rx.el.div(
        rx.el.div(
            rx.el.h3(
                row["category"],
                class_name=(
                    "font-['Playfair_Display'] font-bold text-base "
                    "text-[color:var(--purch-ink)]"
                ),
            ),
            _status_pill(row["status"]),
            class_name="flex items-center justify-between gap-2 mb-3",
        ),
        rx.el.div(
            rx.el.span(
                rx.el.span(
                    "₱",
                    class_name="text-sm text-[color:var(--purch-muted)] mr-0.5",
                ),
                row["spent"].to_string(),
                class_name=(
                    "font-['DM_Mono'] text-2xl font-bold "
                    "text-[color:var(--purch-ink)]"
                ),
            ),
            rx.el.span(
                " / ₱",
                row["limit_amount"].to_string(),
                class_name=(
                    "font-['DM_Mono'] text-xs text-[color:var(--purch-muted)] ml-1"
                ),
            ),
            class_name="flex items-baseline mb-2",
        ),
        rx.el.div(
            rx.el.div(
                class_name=fill_class,
                style={
                    "width": rx.cond(
                        row["pct"] > 100,
                        "100%",
                        row["pct"].to_string() + "%",
                    )
                },
            ),
            class_name=(
                "h-2 rounded-full bg-[color:var(--purch-border)] overflow-hidden"
            ),
        ),
        rx.el.div(
            rx.el.span(
                row["pct"].to_string(),
                "% used",
                class_name=(
                    "font-['DM_Mono'] text-[0.65rem] text-[color:var(--purch-muted)]"
                ),
            ),
            rx.cond(
                row["remaining"] >= 0,
                rx.el.span(
                    "₱",
                    row["remaining"].to_string(),
                    " left",
                    class_name=(
                        "font-['DM_Mono'] text-[0.65rem] "
                        "text-[color:var(--purch-teal)]"
                    ),
                ),
                rx.el.span(
                    "₱",
                    (row["remaining"] * -1).to_string(),
                    " over",
                    class_name=(
                        "font-['DM_Mono'] text-[0.65rem] "
                        "text-[color:var(--purch-danger)]"
                    ),
                ),
            ),
            class_name="flex items-center justify-between mt-1.5",
        ),
        class_name=f"{CLASSES['card']} p-5",
    )


def _budgets_section() -> rx.Component:
    return rx.el.section(
        _section_heading(
            "Budget status",
            "This month vs. plan",
            rx.cond(
                AnalyticsState.has_budgets,
                rx.el.span(
                    AnalyticsState.budget_status.length().to_string(),
                    " active",
                    class_name=(
                        "font-['DM_Mono'] text-[0.65rem] "
                        "text-[color:var(--purch-muted)]"
                    ),
                ),
                rx.fragment(),
            ),
        ),
        rx.cond(
            AnalyticsState.has_budgets,
            rx.el.div(
                rx.foreach(AnalyticsState.budget_status, _budget_card),
                class_name=(
                    "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
                ),
            ),
            rx.el.div(
                rx.el.p(
                    "No budgets set yet.",
                    class_name=(
                        "font-['Playfair_Display'] font-bold text-lg "
                        "text-[color:var(--purch-ink)] mb-1"
                    ),
                ),
                rx.el.p(
                    "In chat, say 'set food budget to 3000' and it'll appear here.",
                    class_name="text-sm text-[color:var(--purch-muted)]",
                ),
                class_name="py-10 text-center",
            ),
        ),
    )


# ---------------------------------------------------------------------- #
# Recent transactions
# ---------------------------------------------------------------------- #


def _recent_row(tx: RecentTx) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.p(
                tx["item"],
                class_name=(
                    "text-sm font-semibold text-[color:var(--purch-ink)] "
                    "truncate m-0 leading-tight"
                ),
            ),
            rx.el.p(
                rx.el.span(
                    tx["category"],
                    class_name=(
                        "inline-flex items-center rounded-full px-2 py-0.5 "
                        "text-[0.6rem] font-bold uppercase tracking-wider "
                        "bg-[color:var(--purch-parchment)] "
                        "text-[color:var(--purch-muted)] mr-2"
                    ),
                ),
                rx.el.span(
                    tx["tx_timestamp"],
                    class_name=(
                        "font-['DM_Mono'] text-[0.65rem] "
                        "text-[color:var(--purch-muted)]"
                    ),
                ),
                class_name="mt-1 m-0",
            ),
            class_name="flex-1 min-w-0",
        ),
        rx.el.div(
            rx.el.span(
                "₱",
                tx["amount"].to_string(),
                class_name=(
                    "font-['DM_Mono'] text-sm font-bold "
                    "text-[color:var(--purch-coral)]"
                ),
            ),
            class_name="ml-3 shrink-0",
        ),
        class_name=(
            "flex items-start justify-between py-3 "
            "border-b border-dashed border-[color:var(--purch-border)] "
            "last:border-b-0"
        ),
    )


def _recent_section() -> rx.Component:
    return rx.el.section(
        _section_heading(
            "Latest activity",
            "Recent transactions",
            rx.el.span(
                "Last ",
                AnalyticsState.recent_transactions.length().to_string(),
                class_name=(
                    "font-['DM_Mono'] text-[0.65rem] "
                    "text-[color:var(--purch-muted)]"
                ),
            ),
        ),
        rx.cond(
            AnalyticsState.has_recent,
            rx.el.div(
                rx.foreach(AnalyticsState.recent_transactions, _recent_row),
            ),
            _empty_note("Nothing logged yet."),
        ),
        class_name=f"{CLASSES['card']} p-6",
    )


# ---------------------------------------------------------------------- #
# Loading / error / empty top-level states
# ---------------------------------------------------------------------- #


def loading_skeleton() -> rx.Component:
    def _sk_card() -> rx.Component:
        return rx.el.div(
            _skeleton_line("w-20"),
            rx.el.div(class_name="h-6"),
            _skeleton_line("w-32"),
            rx.el.div(class_name="h-3"),
            _skeleton_line("w-16"),
            class_name=f"{CLASSES['card']} p-5",
        )

    return rx.el.div(
        rx.el.div(
            _sk_card(),
            _sk_card(),
            _sk_card(),
            _sk_card(),
            class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4",
        ),
        rx.el.div(
            rx.el.div(class_name=f"{CLASSES['card']} p-6 h-64 animate-pulse"),
            rx.el.div(class_name=f"{CLASSES['card']} p-6 h-64 animate-pulse"),
            class_name="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-6",
        ),
        class_name="w-full",
    )


def error_banner() -> rx.Component:
    return rx.cond(
        AnalyticsState.error_text != "",
        rx.el.div(
            rx.el.span(
                "⚠",
                class_name="text-[color:var(--purch-danger)] font-bold text-lg",
            ),
            rx.el.p(
                AnalyticsState.error_text,
                class_name="text-sm text-[color:var(--purch-ink)] flex-1 m-0",
            ),
            rx.el.button(
                "Retry",
                on_click=AnalyticsState.refresh,
                type="button",
                class_name=(
                    "text-xs font-semibold text-[color:var(--purch-coral)] "
                    "hover:text-[color:var(--purch-coral-light)] transition-colors"
                ),
            ),
            class_name=(
                "flex items-center gap-3 mb-6 p-4 rounded-xl "
                "border border-[color:var(--purch-danger)] "
                "bg-[color:var(--purch-paper)]"
            ),
        ),
        rx.fragment(),
    )


def unauthenticated_banner() -> rx.Component:
    """Rendered on analytics when no identity is active. Sign-in and
    guest CTAs preserve the same coral-primary / outline pattern used
    on the login page so the visual language stays consistent."""
    from purch.states.auth_state import AuthState

    return rx.el.div(
        rx.el.div(
            "P",
            class_name=(
                "w-16 h-16 rounded-2xl bg-[color:var(--purch-dark)] "
                "text-[color:var(--purch-gold)] font-['Playfair_Display'] font-bold "
                "text-3xl flex items-center justify-center"
            ),
        ),
        rx.el.h3(
            "Sign in to see your analytics.",
            class_name=(
                "font-['Playfair_Display'] font-bold text-2xl mt-4 "
                "text-[color:var(--purch-ink)]"
            ),
        ),
        rx.el.p(
            "Your spending trend, category breakdown, and budget status "
            "stay tied to your account. Sign in with Google or email — or "
            "continue as a guest to preview privately on this device.",
            class_name=(
                "text-base text-[color:var(--purch-muted)] mt-3 max-w-md "
                "text-center leading-relaxed"
            ),
        ),
        rx.el.div(
            rx.el.a(
                "Sign in",
                href="/login",
                class_name=CLASSES["primary_button"],
            ),
            rx.el.button(
                "Continue as guest",
                on_click=AuthState.sign_in_as_guest,
                type="button",
                class_name=CLASSES["outline_button"],
            ),
            class_name="flex flex-wrap items-center justify-center gap-3 mt-6",
        ),
        class_name=(
            f"{CLASSES['card']} p-12 flex flex-col items-center "
            "justify-center text-center"
        ),
    )


def unavailable_banner() -> rx.Component:
    return rx.el.div(
        rx.el.div("📊", class_name="text-4xl"),
        rx.el.h3(
            "Analytics needs the cloud database",
            class_name=(
                "font-['Playfair_Display'] font-bold text-xl mt-3 "
                "text-[color:var(--purch-ink)]"
            ),
        ),
        rx.el.p(
            "Analytics reads aggregate data from your Supabase/Postgres "
            "instance. Set REFLEX_DB_URL to enable this page — the chat "
            "experience still works locally on SQLite in the meantime.",
            class_name=(
                "text-sm text-[color:var(--purch-muted)] mt-2 max-w-md "
                "text-center leading-relaxed"
            ),
        ),
        class_name=(
            f"{CLASSES['card']} p-12 flex flex-col items-center justify-center "
            "text-center"
        ),
    )


def empty_dashboard() -> rx.Component:
    return rx.el.div(
        rx.el.div("🧾", class_name="text-4xl"),
        rx.el.h3(
            "No activity yet",
            class_name=(
                "font-['Playfair_Display'] font-bold text-xl mt-3 "
                "text-[color:var(--purch-ink)]"
            ),
        ),
        rx.el.p(
            "Log your first purchase in chat and it'll show up here — "
            "spending by category, day-over-day trend, and budget usage.",
            class_name=(
                "text-sm text-[color:var(--purch-muted)] mt-2 max-w-md "
                "text-center leading-relaxed"
            ),
        ),
        rx.el.a(
            "Open the chat →",
            href="/chat",
            class_name=CLASSES["primary_button"] + " mt-5",
        ),
        class_name=(
            f"{CLASSES['card']} p-12 flex flex-col items-center justify-center "
            "text-center"
        ),
    )


# ---------------------------------------------------------------------- #
# Composed dashboard body
# ---------------------------------------------------------------------- #


def dashboard_body() -> rx.Component:
    return rx.el.div(
        _kpi_row(),
        rx.el.div(
            _category_section(),
            _trend_section(),
            class_name="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-6",
        ),
        rx.el.div(
            _wallet_section(),
            class_name="mt-6",
        ),
        rx.el.div(
            _budgets_section(),
            class_name="mt-6",
        ),
        rx.el.div(
            _recent_section(),
            class_name="mt-6",
        ),
        class_name="w-full",
    )
