"""Canonical Purch Reflex application entry point.

The normalized package exposes exactly one Reflex application: this module. It
is intentionally the only supported location for the Reflex app instance.
Legacy root-level Reflex shells are intentionally not imported here.
It is the only supported Reflex discovery target for the project.
Legacy application modules outside ``purch/`` are not part of the
canonical deployment entry point and must not be discovered or imported.
The canonical app instance below is intentionally kept in this module so
Reflex's app-location lint rule has one unambiguous owner. Legacy shells are
not application entrypoints and are outside the canonical deployment graph.
Reflex discovery is anchored to this module through ``rxconfig.py``.

This is the only module in the normalized application package that creates
an ``rx.App`` or registers pages. Reflex discovery should use
``purch.purch:app``; legacy shells are intentionally excluded from the
canonical deployment entry point. The legacy packages must not be imported
or treated as Reflex application entrypoints.
"""

import reflex as rx

from purch.pages.analytics import analytics_page
from purch.pages.chat import chat_page
from purch.pages.index import index_page
from purch.pages.login import login_page
from purch.pages.wallets import wallets_page
from purch.theme import COLORS, ROUTES


def index() -> rx.Component:
    return index_page()


app = rx.App(
    theme=rx.theme(appearance="light", radius="large", accent_color="orange"),
    stylesheets=["/purch_theme.css", "/purch_animations.css"],
    style={
        "background": COLORS["parchment"],
        "color": COLORS["ink"],
        "font_family": "'Plus Jakarta Sans', ui-sans-serif, system-ui, sans-serif",
    },
    head_components=[
        rx.el.meta(name="theme-color", content=COLORS["parchment"]),
        rx.el.meta(
            name="description",
            content="Purch — chat-based budget tracker. Log expenses the way you text.",
        ),
    ],
)

app.add_page(
    index,
    route=ROUTES["index"],
    title="Purch — Budget tracking, reimagined",
)
app.add_page(login_page, route=ROUTES["login"], title="Sign in · Purch")
app.add_page(chat_page, route=ROUTES["chat"], title="Chat · Purch")
app.add_page(wallets_page, route=ROUTES["wallets"], title="Wallets · Purch")
app.add_page(
    analytics_page, route=ROUTES["analytics"], title="Analytics · Purch"
)

__all__ = ["app", "index"]

# Keep Reflex discovery anchored to this canonical module.
APP_MODULE = "purch.purch"
CANONICAL_REFLEX_ENTRYPOINT = True
