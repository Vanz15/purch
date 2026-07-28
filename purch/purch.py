"""Canonical Purch Reflex application entry point.

The normalized ``purch`` package owns the sole Reflex App instance and all
page registrations. This module is the only Reflex application entry point.
"""

import reflex as rx

# Bootstrap the shared SQLite database on process start. `purch.backend`
# re-exports the root agent/llm/db packages under a normalized namespace.
from purch import backend

backend.bootstrap()

from purch.pages.analytics import analytics_page
from purch.pages.chat import chat_page
from purch.pages.index import index_page
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
    index, route=ROUTES["index"], title="Purch — Budget tracking, reimagined"
)
app.add_page(chat_page, route=ROUTES["chat"], title="Chat · Purch")
app.add_page(
    analytics_page, route=ROUTES["analytics"], title="Analytics · Purch"
)
