"""Purch app sidebar/drawer — budgets, tone, profile, nav.

Rendered as a fixed-position panel on the left of chat/analytics pages.
Visibility is driven by `NavState.sidebar_open`; the header's ☰ / ✕
toggle flips that flag and this component slides in/out accordingly.
"""

import reflex as rx

from purch.states.nav_state import NavState
from purch.states.sidebar_state import BudgetRow, SidebarState
from purch.theme import ROUTES

_CATEGORY_EMOJI: dict[str, str] = {
    "Food": "🍽️",
    "Transport": "🚌",
    "Bills": "🧾",
    "Shopping": "🛍️",
    "Entertainment": "🎮",
    "Health": "❤️",
    "Personal Care": "🧴",
    "Other": "🗂️",
}

_TONE_EMOJI: dict[str, str] = {
    "nonchalant": "🤍",
    "bestie": "✨",
    "sarcastic": "🙄",
    "coach": "💪",
    "rich tita": "💅",
    "kapampangan": "🍖",
}


def _total_budget_card() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            "This Month — Total",
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
                style={"width": SidebarState.total_pct.to_string() + "%"},
            ),
            class_name="h-1.5 rounded-full bg-[color:var(--purch-dark-mid)] overflow-hidden",
        ),
        rx.el.div(
            rx.el.span(
                SidebarState.total_pct.to_string() + "%",
                class_name="font-['DM_Mono'] text-[0.6rem] text-[color:var(--purch-parchment)]/70",
            ),
            rx.el.span(
                "₱" + SidebarState.total_limit.to_string(),
                class_name="font-['DM_Mono'] text-[0.6rem] text-[color:var(--purch-parchment)]/70",
            ),
            class_name="flex items-center justify-between mt-1",
        ),
        class_name="bg-[color:var(--purch-dark)] rounded-xl p-4 mb-4",
    )


def _budget_row(row: BudgetRow) -> rx.Component:
    icon = _CATEGORY_EMOJI.get(row["category"], "🗂️")
    return rx.cond(
        row["limit"] > 0,
        rx.el.div(
            rx.el.div(
                rx.el.span(
                    icon + " " + row["category"],
                    class_name="text-xs font-medium text-[color:var(--purch-ink)]",
                ),
                rx.el.span(
                    "₱" + row["spent"].to_string(),
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
                            row["pct"].to_string() + "%",
                        )
                    },
                ),
                class_name="h-1 rounded-full bg-[color:var(--purch-border)] overflow-hidden",
            ),
            rx.el.div(
                rx.el.span(
                    row["pct"].to_string() + "%",
                    class_name="font-['DM_Mono'] text-[0.6rem] text-[color:var(--purch-muted)]",
                ),
                rx.el.span(
                    "₱" + row["limit"].to_string(),
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
            SidebarState.has_any_budget,
            rx.el.div(rx.foreach(SidebarState.budget_rows, _budget_row)),
            rx.el.p(
                "No budgets set yet — try 'set food budget to 3000' in chat.",
                class_name="text-[0.7rem] text-[color:var(--purch-muted)] italic",
            ),
        ),
        class_name="mb-4",
    )


def _tone_option(tone: str) -> rx.Component:
    emoji = _TONE_EMOJI.get(tone, "•")
    label = tone.title()
    is_active = SidebarState.current_tone == tone
    return rx.el.button(
        rx.el.span(emoji, class_name="mr-1.5"),
        rx.el.span(label),
        on_click=lambda: SidebarState.set_tone(tone),
        type="button",
        class_name=rx.cond(
            is_active,
            (
                "flex items-center px-2.5 py-1.5 rounded-full text-[0.7rem] font-semibold "
                "bg-[color:var(--purch-coral)] text-white transition-colors"
            ),
            (
                "flex items-center px-2.5 py-1.5 rounded-full text-[0.7rem] font-medium "
                "bg-[color:var(--purch-paper)] border border-[color:var(--purch-border)] "
                "text-[color:var(--purch-ink)] hover:border-[color:var(--purch-coral)] "
                "hover:text-[color:var(--purch-coral)] transition-colors"
            ),
        ),
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
        rx.el.div(
            rx.foreach(SidebarState.tone_options, _tone_option),
            class_name="flex flex-wrap gap-1.5",
        ),
        class_name="mb-4",
    )


def _nav_section() -> rx.Component:
    def link(label: str, icon: str, href: str) -> rx.Component:
        return rx.el.a(
            rx.el.span(icon, class_name="mr-2"),
            rx.el.span(label),
            href=href,
            class_name=(
                "flex items-center px-2 py-2 rounded-lg text-sm font-medium "
                "text-[color:var(--purch-ink)] hover:bg-[color:var(--purch-paper)] "
                "hover:text-[color:var(--purch-coral)] transition-colors"
            ),
        )

    return rx.el.div(
        rx.el.p(
            "Navigate",
            class_name=(
                "font-['DM_Mono'] text-[0.6rem] uppercase tracking-[0.08em] "
                "text-[color:var(--purch-muted)] mb-2"
            ),
        ),
        link("Chat", "💬", ROUTES["chat"]),
        link("Analytics", "📊", ROUTES["analytics"]),
        link("Home", "🏠", ROUTES["index"]),
        class_name="mb-4 flex flex-col gap-0.5",
    )


def _profile_section() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                "P",
                class_name=(
                    "w-9 h-9 rounded-full bg-[color:var(--purch-dark)] "
                    "text-[color:var(--purch-gold)] font-['Playfair_Display'] "
                    "font-bold text-sm flex items-center justify-center flex-shrink-0"
                ),
            ),
            rx.el.div(
                rx.el.p(
                    SidebarState.display_name,
                    class_name="text-xs font-bold text-[color:var(--purch-ink)] truncate m-0",
                ),
                rx.el.p(
                    "Session active",
                    class_name=(
                        "font-['DM_Mono'] text-[0.55rem] uppercase tracking-[0.06em] "
                        "text-[color:var(--purch-muted)] m-0"
                    ),
                ),
                class_name="flex-1 min-w-0",
            ),
            class_name="flex items-center gap-2.5",
        ),
        rx.el.a(
            "Sign in",
            href=ROUTES["login"],
            class_name=(
                "block mt-3 text-center text-xs font-semibold "
                "text-[color:var(--purch-coral)] hover:text-[color:var(--purch-coral-light)] "
                "transition-colors"
            ),
        ),
        class_name="pt-4 border-t border-[color:var(--purch-border)]",
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
                    _total_budget_card(),
                    _budgets_section(),
                    _tone_section(),
                    _nav_section(),
                    _profile_section(),
                    class_name="p-4 h-full overflow-y-auto",
                ),
                class_name=(
                    "fixed top-12 left-0 bottom-0 z-40 "
                    "w-72 bg-[color:var(--purch-parchment)] "
                    "border-r border-[color:var(--purch-border)] "
                    "shadow-lg lg:shadow-none purch-fade-in"
                ),
                on_mount=SidebarState.refresh,
            ),
            class_name="",
        ),
        rx.fragment(),
    )
