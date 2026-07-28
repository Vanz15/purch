"""Shared page shell — every Reflex page renders through `page_shell`."""

import reflex as rx

from purch.components.header import header
from purch.components.sidebar import sidebar
from purch.states.nav_state import NavState
from purch.theme import CLASSES


def _inner_class(wide: bool) -> str:
    return (
        "w-full min-h-[calc(100vh-3rem)]"
        if wide
        else "max-w-[1600px] mx-auto w-full px-4 sm:px-6 py-8"
    )


def page_shell(
    *content: rx.Component,
    wide: bool = False,
    with_sidebar: bool = False,
) -> rx.Component:
    """Standard page wrapper.

    Args:
        wide: drop the readable max-width column (used by the login/index splits).
        with_sidebar: render the app drawer and reserve room for it on desktop
            when open. Used by chat/analytics.
    """
    return rx.el.div(
        header(),
        rx.cond(with_sidebar, sidebar(), rx.fragment()),
        rx.el.main(
            rx.el.div(*content, class_name=_inner_class(wide)),
            class_name=rx.cond(
                with_sidebar,
                rx.cond(
                    NavState.sidebar_open,
                    "pt-12 lg:pl-72 transition-[padding] duration-200",
                    "pt-12 transition-[padding] duration-200",
                ),
                "pt-12",
            ),
        ),
        class_name=CLASSES["page"],
    )
