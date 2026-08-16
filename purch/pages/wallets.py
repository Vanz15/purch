"""Wallets page — manual wallet management (no account details ever)."""

import reflex as rx

from purch.components.layout import page_shell
from purch.components.wallet_sections import (
    archived_section,
    empty_wallets,
    message_banners,
    signin_notice,
    summary_row,
    unavailable_notice,
    wallet_form,
    wallet_grid,
)
from purch.states.auth_state import AuthState
from purch.states.wallet_state import WalletState
from purch.theme import CLASSES


def _header_row() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div("Money sources", class_name=CLASSES["eyebrow"]),
            rx.el.h1(
                "Wallets",
                class_name=(
                    "font-['Playfair_Display'] font-bold tracking-tight "
                    "text-3xl sm:text-4xl text-[color:var(--purch-ink)] mt-1"
                ),
            ),
            rx.el.p(
                "Nickname each place your money sits. Purch subtracts a "
                "purchase from the wallet you pick in chat.",
                class_name=(
                    "text-sm text-[color:var(--purch-secondary-text)] mt-2 "
                    "max-w-xl"
                ),
            ),
            class_name="flex-1 min-w-0",
        ),
        rx.el.div(
            rx.el.button(
                rx.cond(WalletState.is_loading, "Refreshing…", "↻ Refresh"),
                on_click=WalletState.refresh,
                disabled=WalletState.is_loading,
                type="button",
                class_name=(
                    CLASSES["outline_button"]
                    + " text-sm disabled:opacity-60 disabled:cursor-not-allowed"
                ),
            ),
            rx.el.button(
                "+ New wallet",
                on_click=WalletState.open_create,
                type="button",
                class_name=CLASSES["primary_button"] + " text-sm",
            ),
            class_name="flex items-center gap-2",
        ),
        class_name=(
            "flex flex-col sm:flex-row sm:items-end sm:justify-between "
            "gap-3 mb-6"
        ),
    )


def _content() -> rx.Component:
    return rx.cond(
        ~AuthState.is_authenticated,
        signin_notice(),
        rx.cond(
            WalletState.unavailable,
            unavailable_notice(),
            rx.el.div(
                summary_row(),
                wallet_form(),
                rx.cond(
                    WalletState.has_wallets,
                    wallet_grid(),
                    rx.cond(
                        WalletState.form_open,
                        rx.fragment(),
                        empty_wallets(),
                    ),
                ),
                archived_section(),
            ),
        ),
    )


def wallets_page() -> rx.Component:
    return page_shell(
        rx.el.div(
            _header_row(),
            message_banners(),
            _content(),
            class_name="w-full max-w-6xl mx-auto",
            on_mount=WalletState.on_load,
        ),
        with_sidebar=True,
    )
