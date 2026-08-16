"""Canonical Purch Reflex application entry point.

This is the only module under the normalized package that creates the Reflex
application or registers pages. Reflex discovery is anchored here through
``rxconfig.py``; legacy shells are intentionally outside the deployment graph.

The legacy Reflex packages are not imported by this canonical entry point;
all routes and components are owned by the ``purch`` package.
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
