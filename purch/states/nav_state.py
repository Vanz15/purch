"""Lightweight nav state for the Reflex shell.

Real auth + chat state land in later phases. For now this just tracks
whether the sidebar is open so the shared layout can render deterministically.
"""

import reflex as rx


class NavState(rx.State):
    sidebar_open: bool = True

    @rx.event
    def toggle_sidebar(self) -> None:
        self.sidebar_open = not self.sidebar_open
