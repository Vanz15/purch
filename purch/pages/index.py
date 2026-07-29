"""Landing page — marketing-style hero introducing Purch."""

import reflex as rx

from purch.theme import CLASSES, ROUTES

_TONE_CHIPS = [
    "Nonchalant",
    "Bestie",
    "Sarcastic",
    "Coach",
    "Rich Tita",
    "Kapampangan",
]


def _tone_chip(tone: str) -> rx.Component:
    return rx.el.span(tone, class_name="purch-chip")


def _tone_row() -> rx.Component:
    return rx.el.div(
        rx.foreach(_TONE_CHIPS, _tone_chip),
        class_name="flex flex-wrap gap-2 mt-6",
    )


def _hero() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                "Purch",
                class_name="font-['Playfair_Display'] font-bold text-3xl text-[color:var(--purch-gold)]",
            ),
            rx.el.div(
                "Budget tracking, reimagined", class_name=CLASSES["eyebrow"]
            ),
            rx.el.h1(
                "Your last ",
                rx.el.em(
                    "eventually",
                    class_name="italic text-[color:var(--purch-coral-light)]",
                ),
                rx.el.br(),
                "leads to another.",
                class_name=f"{CLASSES['display_heading']} text-5xl sm:text-6xl lg:text-7xl leading-[1.02] mt-3 text-[color:var(--purch-parchment)]",
            ),
            rx.el.p(
                "Log expenses the way you text — casually. Purch extracts the item, "
                "amount, and category, and reacts in the tone you pick. No forms, "
                "no dropdowns — just chat.",
                class_name="mt-5 max-w-xl text-[color:var(--purch-muted)] leading-relaxed",
            ),
            _tone_row(),
            rx.el.div(
                rx.el.a(
                    "Open the chat →",
                    href=ROUTES["chat"],
                    class_name=CLASSES["primary_button"],
                ),
                rx.el.a(
                    "Sign in",
                    href=ROUTES["login"],
                    class_name=(
                        "inline-flex items-center justify-center gap-2 rounded-xl "
                        "border border-[color:var(--purch-border)]/40 text-[color:var(--purch-parchment)] "
                        "hover:border-[color:var(--purch-coral-light)] hover:text-[color:var(--purch-coral-light)] "
                        "font-medium px-4 py-2.5 transition-colors"
                    ),
                ),
                class_name="mt-8 flex flex-wrap items-center gap-3",
            ),
            class_name="flex flex-col justify-center gap-5 px-6 sm:px-10 lg:px-16 py-16 lg:py-20",
        ),
        class_name="bg-[color:var(--purch-dark)] flex items-center",
    )


def _preview_card() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.span(
                "PURCH RECEIPT",
                class_name="font-['DM_Mono'] text-[0.7rem] text-[color:var(--purch-gold)]",
            ),
            rx.el.span(
                "✨ Bestie",
                class_name="font-['DM_Mono'] text-[0.7rem] text-[color:var(--purch-muted)]",
            ),
            class_name="flex items-center justify-between bg-[color:var(--purch-dark)] px-4 py-2 rounded-t-2xl",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    "bought a phone case for 350",
                    class_name="purch-bubble-user text-sm max-w-[80%]",
                ),
                class_name="flex justify-end mb-3",
            ),
            rx.el.div(
                rx.el.div(
                    "Logged! Phone case ₱350 under Shopping. 🛍️",
                    class_name="purch-bubble-assistant text-sm max-w-[80%]",
                ),
                class_name="flex justify-start mb-3",
            ),
            rx.el.div(
                rx.el.div(
                    "how much this week?",
                    class_name="purch-bubble-user text-sm max-w-[80%]",
                ),
                class_name="flex justify-end mb-3",
            ),
            rx.el.div(
                rx.el.div(
                    "You spent ₱2,450 this week — most of it on Food. 🍽️",
                    class_name="purch-bubble-assistant text-sm max-w-[80%]",
                ),
                class_name="flex justify-start",
            ),
            class_name="bg-[color:var(--purch-paper)] p-5 rounded-b-2xl",
        ),
        class_name="w-full max-w-md border border-[color:var(--purch-border)] rounded-2xl overflow-hidden shadow-[var(--purch-shadow-md)]",
    )


def _showcase() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            _preview_card(),
            rx.el.div(
                rx.el.h2(
                    "Own it. Log it.",
                    class_name=f"{CLASSES['display_heading']} text-2xl",
                ),
                rx.el.p(
                    "Whether it's your first expense or your thousandth, Purch is ready when you are.",
                    class_name="text-sm text-[color:var(--purch-secondary-text)] mt-1",
                ),
                rx.el.a(
                    "Start tracking",
                    href=ROUTES["login"],
                    class_name=f"{CLASSES['primary_button']} mt-4 w-full",
                ),
                class_name=f"{CLASSES['card']} p-6 mt-6 w-full max-w-md",
            ),
            class_name="flex flex-col items-center justify-center px-6 sm:px-10 lg:px-16 py-16",
        ),
        class_name="bg-[color:var(--purch-parchment)]",
    )


def index_page() -> rx.Component:
    return rx.el.main(
        rx.el.div(
            _hero(),
            _showcase(),
            class_name="grid grid-cols-1 lg:grid-cols-2 w-full min-h-screen",
        ),
        class_name="min-h-screen w-full bg-[color:var(--purch-parchment)]",
    )
