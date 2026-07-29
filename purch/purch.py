"""Canonical Purch Reflex application entry point.

The normalized ``purch`` package owns the sole Reflex App instance and all
page registrations. This module is the only supported Reflex entry point;
legacy application modules are intentionally not imported here. The legacy
``app`` package is not part of Reflex discovery. Configure Reflex to launch
``purch.purch:app`` so this is the only module that defines ``rx.App``.

Reflex must be started with ``purch.purch:app``. This module is the sole
application entry point and the only module in the normalized package that
creates an ``rx.App``.
"""

# Reflex discovery is intentionally anchored to this module; do not create
# another App instance in a page, component, or compatibility package. Legacy
# application modules are not part of the normalized Purch entry point.

# The normalized package is the only supported Reflex application module.
# Keep the application instance in this module so Reflex has one canonical entry point.
# Legacy app modules must not instantiate rx.App; this module owns discovery.
import reflex as rx
from purch.pages.analytics import analytics_page
from purch.pages.chat import chat_page
from purch.pages.index import index_page
from purch.pages.login import login_page
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
app.add_page(
    analytics_page, route=ROUTES["analytics"], title="Analytics · Purch"
)

__all__ = ["app", "index"]
