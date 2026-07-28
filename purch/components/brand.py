"""Purch wordmark — Playfair display with optional Beta pill."""

import reflex as rx


def brand(show_beta: bool = True, size: str = "md") -> rx.Component:
    size_class = {
        "sm": "text-lg",
        "md": "text-xl",
        "lg": "text-3xl",
        "xl": "text-5xl",
    }.get(size, "text-xl")

    return rx.el.div(
        rx.el.span(
            "Purch",
            class_name=f"font-['Playfair_Display'] font-bold {size_class} leading-none text-[color:var(--purch-ink)]",
        ),
        rx.cond(
            show_beta,
            rx.el.span("Beta", class_name="purch-beta-badge"),
            rx.fragment(),
        ),
        class_name="inline-flex items-center gap-2",
    )
