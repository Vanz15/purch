"""Purch Reflex shell entry point.

This is a new shell that lives alongside the existing Streamlit app
(`app.py` at repo root, plus `ui/`). The Streamlit implementation is
intentionally left untouched so we can migrate incrementally — see
MIGRATION.md at the repo root for the full analysis and remaining work.
"""

import reflex as rx

from app.pages.index import index_page
from app.pages.login import login_page
from app.pages.chat import chat_page
from app.pages.analytics import analytics_page
from app.theme import COLORS, ROUTES


def index() -> rx.Component:
    return index_page()


# Global styling: keep it CSS-first via `purch_theme.css`, and let Reflex's
# theme provide sensible Radix defaults for any built-in components.
app = rx.App(
    theme=rx.theme(appearance="light", radius="large", accent_color="orange"),
    stylesheets=["/purch_theme.css"],
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
app.add_page(
    analytics_page, route=ROUTES["analytics"], title="Analytics · Purch"
)
