"""Purch Reflex application entry point."""

# Keep the sole Reflex application instance in this module so discovery never
# finds a second App in a page or component module.

import reflex as rx

from app.app.pages.analytics import analytics_page
from app.app.pages.chat import chat_page
from app.app.pages.index import index_page
from app.app.pages.login import login_page
from app.app.theme import COLORS, ROUTES


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
app.add_page(login_page, route=ROUTES["login"], title="Sign in · Purch")
app.add_page(chat_page, route=ROUTES["chat"], title="Chat · Purch")
app.add_page(
    analytics_page, route=ROUTES["analytics"], title="Analytics · Purch"
)
