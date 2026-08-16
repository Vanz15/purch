"""Wallets page sections — summary, wallet cards, form, archive list.

Design language matches the rest of Purch: parchment page, paper cards
with soft borders, Playfair headings, DM Mono numerals/labels, coral
primary actions, gold/teal wallet accents.
"""

from __future__ import annotations

import reflex as rx

from purch.states.wallet_state import WalletRow, WalletState
from purch.theme import CLASSES, ROUTES


def _type_badge(wallet_type: rx.Var, accent: rx.Var) -> rx.Component:
    return rx.el.span(
        wallet_type,
        class_name=rx.match(
            accent,
            (
                "gold",
                "inline-flex items-center rounded-full px-2 py-0.5 "
                "font-['DM_Mono'] text-[0.6rem] uppercase tracking-[0.1em] "
                "bg-[color:var(--purch-gold)]/15 text-[color:var(--purch-gold)]",
            ),
            (
                "teal",
                "inline-flex items-center rounded-full px-2 py-0.5 "
                "font-['DM_Mono'] text-[0.6rem] uppercase tracking-[0.1em] "
                "bg-[color:var(--purch-teal)]/15 text-[color:var(--purch-teal)]",
            ),
            (
                "danger",
                "inline-flex items-center rounded-full px-2 py-0.5 "
                "font-['DM_Mono'] text-[0.6rem] uppercase tracking-[0.1em] "
                "bg-[color:var(--purch-danger)]/10 text-[color:var(--purch-danger)]",
            ),
            "inline-flex items-center rounded-full px-2 py-0.5 "
            "font-['DM_Mono'] text-[0.6rem] uppercase tracking-[0.1em] "
            "bg-[color:var(--purch-parchment)] text-[color:var(--purch-muted)]",
        ),
    )


def summary_row() -> rx.Component:
    def tile(label: str, value: rx.Var, tone: str) -> rx.Component:
        return rx.el.div(
            rx.el.div(label, class_name=CLASSES["eyebrow"]),
            rx.el.div(
                rx.el.span(
                    "₱",
                    class_name="text-lg text-[color:var(--purch-muted)] mr-0.5",
                ),
                rx.el.span(value),
                class_name=(
                    "font-['DM_Mono'] font-bold text-2xl mt-2 "
                    + {
                        "gold": "text-[color:var(--purch-gold)]",
                        "danger": "text-[color:var(--purch-danger)]",
                        "coral": "text-[color:var(--purch-coral)]",
                    }.get(tone, "text-[color:var(--purch-ink)]")
                ),
            ),
            class_name=f"{CLASSES['card']} p-5 w-full",
        )

    return rx.el.div(
        tile("Available", WalletState.assets_display, "coral"),
        tile("Owed / lent out", WalletState.liabilities_display, "danger"),
        tile("Net position", WalletState.net_display, "gold"),
        class_name="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full",
    )


def _wallet_card(wallet: WalletRow) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.h3(
                wallet["name"],
                class_name=(
                    "font-['Playfair_Display'] font-bold text-lg "
                    "text-[color:var(--purch-ink)] m-0 truncate"
                ),
            ),
            _type_badge(wallet["wallet_type"], wallet["accent"]),
            class_name="flex items-center justify-between gap-2",
        ),
        rx.el.div(
            rx.el.span(
                "₱",
                class_name="text-base text-[color:var(--purch-muted)] mr-0.5",
            ),
            rx.el.span(
                wallet["balance_display"],
                class_name=(
                    "font-['DM_Mono'] text-2xl font-bold "
                    "text-[color:var(--purch-ink)]"
                ),
            ),
            class_name="flex items-baseline mt-3",
        ),
        rx.cond(
            wallet["note"] != "",
            rx.el.p(
                wallet["note"],
                class_name=(
                    "text-xs text-[color:var(--purch-muted)] mt-2 "
                    "leading-relaxed m-0"
                ),
            ),
            rx.fragment(),
        ),
        rx.el.div(
            rx.el.button(
                "Edit",
                on_click=lambda: WalletState.open_edit(wallet["id"]),
                type="button",
                class_name=CLASSES["outline_button"] + " text-xs py-1.5 px-3",
            ),
            rx.el.button(
                "Archive",
                on_click=lambda: WalletState.archive_wallet(wallet["id"]),
                type="button",
                class_name=(
                    "text-xs font-semibold text-[color:var(--purch-muted)] "
                    "hover:text-[color:var(--purch-coral)] transition-colors"
                ),
            ),
            class_name=(
                "flex items-center justify-between gap-2 mt-4 pt-3 "
                "border-t border-dashed border-[color:var(--purch-border)]"
            ),
        ),
        class_name=f"{CLASSES['card']} p-5",
    )


def wallet_grid() -> rx.Component:
    return rx.el.div(
        rx.foreach(WalletState.wallets, _wallet_card),
        class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-6",
    )


def _archived_card(wallet: WalletRow) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.span(
                wallet["name"],
                class_name=(
                    "text-sm font-semibold text-[color:var(--purch-muted)]"
                ),
            ),
            _type_badge(wallet["wallet_type"], wallet["accent"]),
            class_name="flex items-center gap-2 flex-1 min-w-0",
        ),
        rx.el.span(
            rx.el.span("₱", wallet["balance_display"]),
            class_name=(
                "font-['DM_Mono'] text-xs text-[color:var(--purch-muted)] mr-3"
            ),
        ),
        rx.el.button(
            "Restore",
            on_click=lambda: WalletState.restore_wallet(wallet["id"]),
            type="button",
            class_name=(
                "text-xs font-semibold text-[color:var(--purch-coral)] "
                "hover:text-[color:var(--purch-coral-light)] transition-colors"
            ),
        ),
        class_name=(
            "flex items-center justify-between gap-2 py-3 "
            "border-b border-dashed border-[color:var(--purch-border)] "
            "last:border-b-0"
        ),
    )


def archived_section() -> rx.Component:
    return rx.cond(
        WalletState.has_archived,
        rx.el.section(
            rx.el.button(
                rx.cond(
                    WalletState.show_archived,
                    "Hide archived wallets",
                    "Show archived wallets",
                ),
                on_click=WalletState.toggle_archived,
                type="button",
                class_name=(
                    "font-['DM_Mono'] text-[0.65rem] uppercase "
                    "tracking-[0.1em] text-[color:var(--purch-muted)] "
                    "hover:text-[color:var(--purch-coral)] transition-colors"
                ),
            ),
            rx.cond(
                WalletState.show_archived,
                rx.el.div(
                    rx.foreach(WalletState.archived_wallets, _archived_card),
                    class_name=f"{CLASSES['card']} p-5 mt-3",
                ),
                rx.fragment(),
            ),
            class_name="mt-8",
        ),
        rx.fragment(),
    )


def _labelled(
    label: str, control: rx.Component, hint: str = ""
) -> rx.Component:
    return rx.el.label(
        rx.el.span(
            label,
            class_name=(
                "font-['DM_Mono'] text-[0.65rem] uppercase "
                "tracking-[0.1em] text-[color:var(--purch-muted)]"
            ),
        ),
        control,
        rx.cond(
            hint != "",
            rx.el.span(
                hint,
                class_name="text-[0.65rem] text-[color:var(--purch-muted)]",
            ),
            rx.fragment(),
        ),
        class_name="flex flex-col gap-1",
    )


_INPUT_CLASS = (
    "mt-1 w-full rounded-xl border border-[color:var(--purch-border)] "
    "bg-[color:var(--purch-paper)] px-3.5 py-2.5 text-sm "
    "placeholder:text-[color:var(--purch-muted)] focus:outline-none "
    "focus:border-[color:var(--purch-coral)]"
)


def wallet_form() -> rx.Component:
    return rx.cond(
        WalletState.form_open,
        rx.el.form(
            rx.el.div(
                rx.el.h2(
                    WalletState.form_title,
                    class_name=(
                        "font-['Playfair_Display'] font-bold text-xl "
                        "text-[color:var(--purch-ink)] m-0"
                    ),
                ),
                rx.el.button(
                    "✕",
                    on_click=WalletState.close_form,
                    type="button",
                    class_name=(
                        "text-[color:var(--purch-muted)] "
                        "hover:text-[color:var(--purch-coral)] transition-colors"
                    ),
                ),
                class_name="flex items-start justify-between gap-3",
            ),
            rx.el.p(
                "Nicknames only — Purch never asks for account numbers, "
                "card numbers, or login details.",
                class_name=(
                    "text-xs text-[color:var(--purch-muted)] mt-1 mb-4 "
                    "leading-relaxed"
                ),
            ),
            rx.el.div(
                _labelled(
                    "Nickname",
                    rx.el.input(
                        name="name",
                        placeholder="e.g. Baon cash, Payday bank",
                        default_value=WalletState.form_name,
                        key=WalletState.form_version,
                        max_length=40,
                        auto_complete="off",
                        class_name=_INPUT_CLASS,
                    ),
                ),
                _labelled(
                    "Type",
                    rx.el.div(
                        rx.el.select(
                            rx.foreach(
                                WalletState.wallet_types,
                                lambda t: rx.el.option(t, value=t),
                            ),
                            name="wallet_type",
                            default_value=WalletState.form_type,
                            key=WalletState.form_version,
                            class_name=_INPUT_CLASS + " appearance-none pr-9",
                        ),
                        rx.icon(
                            "chevron-down",
                            class_name=(
                                "h-4 w-4 absolute right-3 top-1/2 "
                                "-translate-y-1/2 pointer-events-none "
                                "text-[color:var(--purch-muted)]"
                            ),
                        ),
                        class_name="relative",
                    ),
                ),
                _labelled(
                    "Balance (₱)",
                    rx.el.input(
                        name="balance",
                        type="number",
                        step="0.01",
                        min="0",
                        placeholder="0.00",
                        default_value=WalletState.form_balance,
                        key=WalletState.form_version,
                        class_name=_INPUT_CLASS,
                    ),
                ),
                _labelled(
                    "Note (optional)",
                    rx.el.input(
                        name="note",
                        placeholder="What this wallet is for",
                        default_value=WalletState.form_note,
                        key=WalletState.form_version,
                        max_length=120,
                        auto_complete="off",
                        class_name=_INPUT_CLASS,
                    ),
                ),
                class_name="grid grid-cols-1 sm:grid-cols-2 gap-4",
            ),
            rx.el.div(
                rx.el.button(
                    "Cancel",
                    on_click=WalletState.close_form,
                    type="button",
                    class_name=CLASSES["outline_button"] + " text-sm",
                ),
                rx.el.button(
                    WalletState.submit_label,
                    type="submit",
                    class_name=CLASSES["primary_button"] + " text-sm",
                ),
                class_name="flex items-center justify-end gap-2 mt-5",
            ),
            on_submit=WalletState.submit_wallet,
            reset_on_submit=False,
            class_name=f"{CLASSES['card']} p-6 mt-6",
        ),
        rx.fragment(),
    )


def message_banners() -> rx.Component:
    return rx.el.div(
        rx.cond(
            WalletState.error_text != "",
            rx.el.div(
                rx.el.span(
                    "⚠",
                    class_name="text-[color:var(--purch-danger)] font-bold",
                ),
                rx.el.p(
                    WalletState.error_text,
                    class_name="text-sm text-[color:var(--purch-ink)] flex-1 m-0",
                ),
                rx.el.button(
                    "Dismiss",
                    on_click=WalletState.dismiss_message,
                    type="button",
                    class_name=(
                        "text-xs text-[color:var(--purch-muted)] "
                        "hover:text-[color:var(--purch-ink)] transition-colors"
                    ),
                ),
                class_name=(
                    "flex items-center gap-3 p-3 rounded-xl "
                    "border border-[color:var(--purch-danger)] "
                    "bg-[color:var(--purch-paper)] mb-3"
                ),
            ),
            rx.fragment(),
        ),
        rx.cond(
            WalletState.info_text != "",
            rx.el.div(
                rx.el.span(
                    "✓", class_name="text-[color:var(--purch-teal)] font-bold"
                ),
                rx.el.p(
                    WalletState.info_text,
                    class_name="text-sm text-[color:var(--purch-ink)] flex-1 m-0",
                ),
                rx.el.button(
                    "Dismiss",
                    on_click=WalletState.dismiss_message,
                    type="button",
                    class_name=(
                        "text-xs text-[color:var(--purch-muted)] "
                        "hover:text-[color:var(--purch-ink)] transition-colors"
                    ),
                ),
                class_name=(
                    "flex items-center gap-3 p-3 rounded-xl "
                    "border border-[color:var(--purch-teal)] "
                    "bg-[color:var(--purch-paper)] mb-3"
                ),
            ),
            rx.fragment(),
        ),
    )


def empty_wallets() -> rx.Component:
    return rx.el.div(
        rx.el.div("👛", class_name="text-4xl"),
        rx.el.h3(
            "No wallets yet",
            class_name=(
                "font-['Playfair_Display'] font-bold text-xl mt-3 "
                "text-[color:var(--purch-ink)]"
            ),
        ),
        rx.el.p(
            "Add a wallet for each place your money sits — cash on hand, "
            "a bank bucket, savings, or money you've lent out. Purch will "
            "subtract purchases from the wallet you pick in chat.",
            class_name=(
                "text-sm text-[color:var(--purch-muted)] mt-2 max-w-md "
                "text-center leading-relaxed"
            ),
        ),
        rx.el.button(
            "Add your first wallet",
            on_click=WalletState.open_create,
            type="button",
            class_name=CLASSES["primary_button"] + " mt-5",
        ),
        class_name=(
            f"{CLASSES['card']} p-12 flex flex-col items-center "
            "justify-center text-center mt-6"
        ),
    )


def unavailable_notice() -> rx.Component:
    return rx.el.div(
        rx.el.div("👛", class_name="text-4xl"),
        rx.el.h3(
            "Wallets need the cloud database",
            class_name=(
                "font-['Playfair_Display'] font-bold text-xl mt-3 "
                "text-[color:var(--purch-ink)]"
            ),
        ),
        rx.el.p(
            "Wallet balances live in your Supabase/Postgres instance. "
            "Chat, budgets, and analytics keep working in the meantime.",
            class_name=(
                "text-sm text-[color:var(--purch-muted)] mt-2 max-w-md "
                "text-center leading-relaxed"
            ),
        ),
        class_name=(
            f"{CLASSES['card']} p-12 flex flex-col items-center "
            "justify-center text-center mt-6"
        ),
    )


def signin_notice() -> rx.Component:
    from purch.states.auth_state import AuthState

    return rx.el.div(
        rx.el.div(
            "P",
            class_name=(
                "w-16 h-16 rounded-2xl bg-[color:var(--purch-dark)] "
                "text-[color:var(--purch-gold)] font-['Playfair_Display'] "
                "font-bold text-3xl flex items-center justify-center"
            ),
        ),
        rx.el.h3(
            "Sign in to manage wallets.",
            class_name=(
                "font-['Playfair_Display'] font-bold text-2xl mt-4 "
                "text-[color:var(--purch-ink)]"
            ),
        ),
        rx.el.p(
            "Wallet nicknames and balances stay tied to your account.",
            class_name=(
                "text-base text-[color:var(--purch-muted)] mt-3 max-w-md "
                "text-center leading-relaxed"
            ),
        ),
        rx.el.div(
            rx.el.a(
                "Sign in",
                href=ROUTES["login"],
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
            "justify-center text-center mt-6"
        ),
    )
