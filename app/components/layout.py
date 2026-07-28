"""Shared page shell — every Reflex page renders through `page_shell`.

Keeps the fixed header, the parchment background, and the max-width main
column in one place so pages only worry about their own content.
"""

import reflex as rx

from app.components.header import header
from app.theme import CLASSES


def _inner_class(wide: bool) -> str:
    return (
        "w-full min-h-[calc(100vh-3rem)]"
        if wide
        else "max-w-[1600px] mx-auto w-full px-4 sm:px-6 py-8"
    )


def page_shell(*content: rx.Component, wide: bool = False) -> rx.Component:
    """Wrap page content in the standard Purch shell.

    Args:
        content: page-level components to render inside <main>.
        wide: when True, drops the readable max-width and lets the page
            span the full viewport (useful for the login split layout).
    """
    return rx.el.div(
        header(),
        rx.el.main(
            rx.el.div(*content, class_name=_inner_class(wide)),
            class_name="pt-12",
        ),
        class_name=CLASSES["page"],
    )
