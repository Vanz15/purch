"""Purch app sidebar/drawer — budgets, tone, profile, nav.

Rendered as a fixed-position panel on the left of chat/analytics pages.
Visibility is driven by `NavState.sidebar_open`; the header's ☰ / ✕
toggle flips that flag and this component slides in/out accordingly.
"""

import reflex as rx

from purch.states.auth_state import AuthState
from purch.states.nav_state import NavState
from purch.states.sidebar_state import BudgetRow, SidebarState, WalletMiniRow
from purch.theme import CLASSES, ROUTES


def _total_budget_card() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            SidebarState.month_display,
            " — Total",
            class_name=(
                "font-['DM_Mono'] text-[0.6rem] uppercase tracking-[0.08em] "
                "text-[color:var(--purch-parchment)]/70 mb-1"
            ),
        ),
        rx.el.div(
            rx.el.span(
                "₱",
                class_name="font-['DM_Mono'] text-lg text-[color:var(--purch-gold)] mr-0.5",
            ),
            rx.el.span(
                SidebarState.total_spent.to_string(),
                class_name="font-['DM_Mono'] text-2xl font-bold text-[color:var(--purch-gold)]",
            ),
            class_name="mb-2",
        ),
        rx.el.div(
            rx.el.div(
                class_name=(
                    "h-full rounded-full bg-gradient-to-r "
                    "from-[color:var(--purch-coral)] to-[color:var(--purch-gold)] "
                    "transition-all"
                ),
                style={
                    "width": rx.cond(
                        SidebarState.total_pct > 100,
                        "100%",
                        f"{SidebarState.total_pct}%",
                    )
                },
            ),
            class_name="h-1.5 rounded-full bg-[color:var(--purch-dark-mid)] overflow-hidden",
        ),
        rx.el.div(
            rx.el.span(
                rx.el.span(SidebarState.total_pct.to_string(), "%"),
                class_name="font-['DM_Mono'] text-[0.6rem] text-[color:var(--purch-parchment)]/70",
            ),
            rx.el.span(
                rx.el.span(
                    "₱",
                    SidebarState.total_limit.to_string(),
                ),
                class_name="font-['DM_Mono'] text-[0.6rem] text-[color:var(--purch-parchment)]/70",
            ),
            class_name="flex items-center justify-between mt-1",
        ),
        class_name="bg-[color:var(--purch-dark)] rounded-xl p-4 mb-4",
    )


def _budget_row(row: BudgetRow) -> rx.Component:
    return rx.cond(
        row["limit"] > 0,
        rx.el.div(
            rx.el.div(
                rx.el.span(
                    rx.match(
                        row["category"],
                        ("Food", "🍽️ Food"),
                        ("Transport", "🚌 Transport"),
                        ("Bills", "🧾 Bills"),
                        ("Shopping", "🛍️ Shopping"),
                        ("Entertainment", "🎮 Entertainment"),
                        ("Health", "❤️ Health"),
                        ("Personal Care", "🧴 Personal Care"),
                        "🗂️ Other",
                    ),
                    class_name="text-xs font-medium text-[color:var(--purch-ink)]",
                ),
                rx.el.span(
                    rx.el.span(
                        "₱",
                        row["spent"].to_string(),
                    ),
                    class_name=rx.cond(
                        row["over"],
                        "font-['DM_Mono'] text-[0.7rem] text-[color:var(--purch-danger)]",
                        "font-['DM_Mono'] text-[0.7rem] text-[color:var(--purch-coral)]",
                    ),
                ),
                class_name="flex items-center justify-between mb-1",
            ),
            rx.el.div(
                rx.el.div(
                    class_name=rx.cond(
                        row["over"],
                        "h-full rounded-full bg-[color:var(--purch-danger)]",
                        "h-full rounded-full bg-[color:var(--purch-coral)]",
                    ),
                    style={
                        "width": rx.cond(
                            row["pct"] > 100,
                            "100%",
                            f"{row['pct']}%",
                        )
                    },
                ),
                class_name="h-1 rounded-full bg-[color:var(--purch-border)] overflow-hidden",
            ),
            rx.el.div(
                rx.el.span(
                    rx.el.span(row["pct"].to_string(), "%"),
                    class_name="font-['DM_Mono'] text-[0.6rem] text-[color:var(--purch-muted)]",
                ),
                rx.el.span(
                    rx.el.span(
                        "₱",
                        row["limit"].to_string(),
                    ),
                    class_name="font-['DM_Mono'] text-[0.6rem] text-[color:var(--purch-muted)]",
                ),
                class_name="flex items-center justify-between mt-0.5",
            ),
            class_name="mb-3",
        ),
        rx.fragment(),
    )


def _budgets_section() -> rx.Component:
    return rx.el.div(
        rx.el.p(
            "Budgets",
            class_name=(
                "font-['DM_Mono'] text-[0.6rem] uppercase tracking-[0.08em] "
                "text-[color:var(--purch-muted)] mb-2"
            ),
        ),
        rx.cond(
            SidebarState.refresh_status != "",
            rx.el.p(
                SidebarState.refresh_status,
                class_name="text-[0.65rem] text-[color:var(--purch-muted)] italic mb-2",
            ),
            rx.fragment(),
        ),
        rx.cond(
            SidebarState.has_any_budget,
            rx.el.div(rx.foreach(SidebarState.budget_rows, _budget_row)),
            rx.el.p(
                "No budgets set yet — try 'set food budget to 3000' in chat.",
                class_name="text-[0.7rem] text-[color:var(--purch-muted)] italic",
            ),
        ),
        class_name="mb-4",
    )


def _tone_section() -> rx.Component:
    return rx.el.div(
        rx.el.p(
            "Tone",
            class_name=(
                "font-['DM_Mono'] text-[0.6rem] uppercase tracking-[0.08em] "
                "text-[color:var(--purch-muted)] mb-2"
            ),
        ),
        rx.select.root(
            rx.select.trigger(
                class_name=(
                    "w-full rounded-xl border border-[color:var(--purch-border)] "
                    "bg-[color:var(--purch-paper)] px-3 py-2 text-sm "
                    "text-[color:var(--purch-ink)] shadow-none outline-none "
                    "transition-colors hover:border-[color:var(--purch-coral)] "
                    "focus:border-[color:var(--purch-coral)] focus:ring-2 "
                    "focus:ring-[color:var(--purch-coral)]/15"
                ),
            ),
            rx.select.content(
                rx.select.group(
                    rx.foreach(
                        SidebarState.tone_options,
                        lambda tone: rx.select.item(
                            tone,
                            value=tone,
                            class_name=(
                                "w-full cursor-pointer rounded-lg px-3 py-2 text-sm "
                                "text-[color:var(--purch-ink)] outline-none "
                                "hover:bg-[color:var(--purch-parchment)] "
                                "focus:bg-[color:var(--purch-parchment)]"
                            ),
                        ),
                    ),
                ),
                class_name=(
                    "z-50 mt-1 w-[var(--radix-select-trigger-width)] rounded-xl "
                    "border border-[color:var(--purch-border)] bg-[color:var(--purch-paper)] "
                    "p-1 text-[color:var(--purch-ink)] shadow-[var(--purch-shadow-md)]"
                ),
                position="popper",
            ),
            value=SidebarState.current_tone,
            on_change=SidebarState.set_tone,
            class_name="w-full",
        ),
        class_name="mb-4",
    )


def _wallet_mini_row(wallet: WalletMiniRow) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.span(
                wallet["name"],
                class_name=(
                    "text-xs font-medium text-[color:var(--purch-ink)] "
                    "truncate max-w-[9rem]"
                ),
            ),
            rx.el.span(
                rx.el.span("\u20b1", wallet["balance_display"]),
                class_name=rx.cond(
                    wallet["is_liability"],
                    "font-['DM_Mono'] text-[0.7rem] text-[color:var(--purch-danger)]",
                    "font-['DM_Mono'] text-[0.7rem] text-[color:var(--purch-teal)]",
                ),
            ),
            class_name="flex items-center justify-between gap-2 mb-1",
        ),
        rx.el.div(
            rx.el.div(
                class_name=rx.match(
                    wallet["accent"],
                    (
                        "gold",
                        "h-full rounded-full bg-[color:var(--purch-gold)]",
                    ),
                    (
                        "teal",
                        "h-full rounded-full bg-[color:var(--purch-teal)]",
                    ),
                    (
                        "danger",
                        "h-full rounded-full bg-[color:var(--purch-danger)]",
                    ),
                    "h-full rounded-full bg-[color:var(--purch-muted)]",
                ),
                style={"width": f"{wallet['pct']}%"},
            ),
            class_name=(
                "h-1 rounded-full bg-[color:var(--purch-border)] overflow-hidden"
            ),
        ),
        rx.el.div(
            wallet["wallet_type"],
            class_name=(
                "font-['DM_Mono'] text-[0.55rem] uppercase "
                "tracking-[0.08em] text-[color:var(--purch-muted)] mt-0.5"
            ),
        ),
        class_name="mb-3",
    )


def _wallet_section() -> rx.Component:
    """Spendable total, owed status, and per-wallet mini bars."""
    return rx.el.div(
        rx.el.p(
            "Wallets",
            class_name=(
                "font-['DM_Mono'] text-[0.6rem] uppercase tracking-[0.08em] "
                "text-[color:var(--purch-muted)] mb-2"
            ),
        ),
        rx.cond(
            SidebarState.wallets_available,
            rx.el.div(
                rx.el.div(
                    rx.el.div(
                        rx.el.div(
                            "Spendable",
                            class_name=(
                                "font-['DM_Mono'] text-[0.55rem] uppercase "
                                "tracking-[0.08em] text-[color:var(--purch-muted)]"
                            ),
                        ),
                        rx.el.div(
                            rx.el.span(
                                "\u20b1",
                                class_name=(
                                    "font-['DM_Mono'] text-sm "
                                    "text-[color:var(--purch-muted)] mr-0.5"
                                ),
                            ),
                            rx.el.span(
                                SidebarState.spendable_display,
                                class_name=(
                                    "font-['DM_Mono'] text-lg font-bold "
                                    "text-[color:var(--purch-teal)]"
                                ),
                            ),
                            class_name="flex items-baseline",
                        ),
                        class_name="flex-1 min-w-0",
                    ),
                    rx.cond(
                        SidebarState.has_liabilities,
                        rx.el.div(
                            rx.el.div(
                                "Owed / lent",
                                class_name=(
                                    "font-['DM_Mono'] text-[0.55rem] uppercase "
                                    "tracking-[0.08em] text-[color:var(--purch-muted)]"
                                ),
                            ),
                            rx.el.span(
                                "\u20b1",
                                SidebarState.liabilities_display,
                                class_name=(
                                    "font-['DM_Mono'] text-sm font-bold "
                                    "text-[color:var(--purch-danger)]"
                                ),
                            ),
                            class_name="text-right shrink-0",
                        ),
                        rx.fragment(),
                    ),
                    class_name=(
                        "flex items-start justify-between gap-2 rounded-xl "
                        "border border-[color:var(--purch-border)] "
                        "bg-[color:var(--purch-paper)] p-3 mb-3"
                    ),
                ),
                rx.cond(
                    SidebarState.has_liabilities,
                    rx.el.div(
                        rx.el.span(
                            "Net position",
                            class_name=(
                                "font-['DM_Mono'] text-[0.55rem] uppercase "
                                "tracking-[0.08em] text-[color:var(--purch-muted)]"
                            ),
                        ),
                        rx.el.span(
                            rx.el.span(
                                "\u20b1", SidebarState.wallet_net_display
                            ),
                            class_name=(
                                "font-['DM_Mono'] text-[0.7rem] "
                                "text-[color:var(--purch-gold)]"
                            ),
                        ),
                        class_name="flex items-center justify-between mb-3",
                    ),
                    rx.fragment(),
                ),
                rx.cond(
                    SidebarState.has_wallets,
                    rx.el.div(
                        rx.foreach(SidebarState.wallet_rows, _wallet_mini_row)
                    ),
                    rx.el.p(
                        "No wallets yet \u2014 add one to track cash, bank, "
                        "savings, or money you've lent.",
                        class_name=(
                            "text-[0.7rem] text-[color:var(--purch-muted)] italic"
                        ),
                    ),
                ),
            ),
            rx.el.p(
                "Wallet balances need the cloud database \u2014 chat and "
                "budgets keep working.",
                class_name="text-[0.7rem] text-[color:var(--purch-muted)] italic",
            ),
        ),
        class_name="mb-4",
    )


def _wallets_link() -> rx.Component:
    return rx.el.a(
        rx.el.span("👛", class_name="text-sm"),
        rx.el.span(
            "Manage wallets",
            class_name="text-xs font-semibold",
        ),
        href=ROUTES["wallets"],
        class_name=(
            "flex items-center gap-2 mb-4 px-3 py-2 rounded-xl "
            "border border-[color:var(--purch-border)] "
            "bg-[color:var(--purch-paper)] text-[color:var(--purch-ink)] "
            "hover:border-[color:var(--purch-teal)] "
            "hover:text-[color:var(--purch-teal)] transition-colors"
        ),
    )


def _profile_avatar() -> rx.Component:
    """Circular avatar: Google picture when available, initial letter for
    email accounts, Purch 'P' mark for guests."""
    initial_letter = rx.cond(
        AuthState.display_name.length() > 0,
        AuthState.display_name[0].upper(),
        rx.cond(
            AuthState.user_email.length() > 0,
            AuthState.user_email[0].upper(),
            "?",
        ),
    )
    google_avatar = rx.el.img(
        src=AuthState.user_picture,
        alt=AuthState.display_name,
        referrer_policy="no-referrer",
        class_name=(
            "w-9 h-9 rounded-full object-cover flex-shrink-0 "
            "border border-[color:var(--purch-border)]"
        ),
    )
    letter_avatar = rx.el.div(
        initial_letter,
        class_name=(
            "w-9 h-9 rounded-full bg-[color:var(--purch-coral)] "
            "text-white font-['Plus_Jakarta_Sans'] font-bold text-sm "
            "flex items-center justify-center flex-shrink-0 uppercase"
        ),
    )
    purch_avatar = rx.el.div(
        "P",
        class_name=(
            "w-9 h-9 rounded-full bg-[color:var(--purch-dark)] "
            "text-[color:var(--purch-gold)] font-['Playfair_Display'] "
            "font-bold text-sm flex items-center justify-center flex-shrink-0"
        ),
    )
    return rx.match(
        AuthState.auth_method,
        (
            "google",
            rx.cond(
                AuthState.user_picture != "",
                google_avatar,
                letter_avatar,
            ),
        ),
        ("email", letter_avatar),
        purch_avatar,
    )


def _profile_section() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            _profile_avatar(),
            rx.el.div(
                rx.el.p(
                    AuthState.display_name,
                    class_name="text-xs font-bold text-[color:var(--purch-ink)] truncate m-0",
                ),
                rx.el.p(
                    rx.match(
                        AuthState.auth_method,
                        ("google", "Signed in with Google"),
                        ("email", AuthState.user_email),
                        ("guest", "Guest session"),
                        "Session active",
                    ),
                    class_name=(
                        "font-['DM_Mono'] text-[0.55rem] uppercase tracking-[0.06em] "
                        "text-[color:var(--purch-muted)] m-0 truncate"
                    ),
                ),
                class_name="flex-1 min-w-0",
            ),
            class_name="flex items-center gap-2.5",
        ),
        rx.el.button(
            "Sign out",
            on_click=AuthState.sign_out,
            type="button",
            class_name=(
                "block w-full mt-3 text-center text-xs font-semibold "
                "text-[color:var(--purch-coral)] hover:text-[color:var(--purch-coral-light)] "
                "transition-colors"
            ),
        ),
        class_name="pt-4 border-t border-[color:var(--purch-border)]",
    )


def _unauthenticated_panel() -> rx.Component:
    """Rendered inside the sidebar when no identity is active. Shows
    the sign-in / guest CTAs instead of the anonymous budgets and tone
    picker."""
    return rx.el.div(
        rx.el.div(
            "P",
            class_name=(
                "w-12 h-12 rounded-2xl bg-[color:var(--purch-dark)] "
                "text-[color:var(--purch-gold)] font-['Playfair_Display'] font-bold "
                "text-2xl flex items-center justify-center mx-auto"
            ),
        ),
        rx.el.h3(
            "You're not signed in.",
            class_name=(
                "font-['Playfair_Display'] font-bold text-base "
                "text-[color:var(--purch-ink)] mt-3 text-center"
            ),
        ),
        rx.el.p(
            "Budgets and tone are tied to your account. "
            "Sign in or continue as a guest to get started.",
            class_name=(
                "text-xs text-[color:var(--purch-muted)] mt-1.5 "
                "leading-relaxed text-center"
            ),
        ),
        rx.el.a(
            "Sign in",
            href=ROUTES["login"],
            class_name=CLASSES["primary_button"] + " w-full mt-4 text-sm",
        ),
        rx.el.button(
            "Continue as guest",
            on_click=AuthState.sign_in_as_guest,
            type="button",
            class_name=CLASSES["outline_button"] + " w-full mt-2 text-sm",
        ),
        class_name=(
            "rounded-xl border border-dashed border-[color:var(--purch-border)] "
            "bg-[color:var(--purch-paper)] p-4"
        ),
    )


def sidebar() -> rx.Component:
    """Slide-in drawer. Visible only when NavState.sidebar_open is True.
    Rendered inside the fixed shell so it overlays content on mobile
    and sits inline on desktop."""
    return rx.cond(
        NavState.sidebar_open,
        rx.el.div(
            rx.el.button(
                on_click=NavState.toggle_sidebar,
                class_name=("fixed inset-0 top-12 z-30 bg-black/20 lg:hidden"),
                aria_label="Close sidebar",
            ),
            rx.el.aside(
                rx.el.div(
                    rx.cond(
                        AuthState.is_authenticated,
                        rx.el.div(
                            _total_budget_card(),
                            _budgets_section(),
                            _wallet_section(),
                            _wallets_link(),
                            _tone_section(),
                            _profile_section(),
                        ),
                        _unauthenticated_panel(),
                    ),
                    class_name="p-4 h-full overflow-y-auto",
                ),
                class_name=(
                    "fixed top-12 left-0 bottom-0 z-40 "
                    "w-72 bg-[color:var(--purch-parchment)] "
                    "border-r border-[color:var(--purch-border)] "
                    "shadow-lg lg:shadow-none purch-fade-in"
                ),
                on_mount=[
                    SidebarState.refresh,
                    rx.call_script(
                        "Intl.DateTimeFormat().resolvedOptions().timeZone",
                        callback=SidebarState.set_timezone,
                    ),
                ],
            ),
            class_name="",
        ),
        rx.fragment(),
    )
