"""Auth state scaffolding for the Reflex shell.

Phase 2 only stubs out the shape of an authenticated session so the login
page and chat page can render conditionally. The actual OAuth token
exchange, cookie signing, and `db.ensure_user` call all land in phase 3
once we pick a provider (see MIGRATION.md §7 — the three candidates are
`reflex-google-auth`, Supabase Auth, or Clerk).

State fields deliberately mirror what `db.models.ensure_user(user_id)`
expects at the boundary: a stable string identifier (email) plus a
display name. Everything else is UI convenience.
"""

import reflex as rx


class AuthState(rx.State):
    # Backend-only session fields. In phase 3 these will be hydrated from
    # a signed cookie / JWT after the OAuth callback completes.
    user_email: str = ""
    user_name: str = ""
    user_picture: str = ""
    is_authenticated: bool = False

    # UI status for the login page. `oauth_status` transitions from
    # "idle" → "redirecting" → ("error" | authenticated).
    oauth_status: str = "idle"
    oauth_error: str = ""

    @rx.event
    def begin_google_login(self):
        """Phase 2 stub — the real handler will call the OAuth provider's
        authorize endpoint (`reflex-google-auth`, Supabase, or Clerk) and
        `rx.redirect` to it. Until credentials are wired up this just
        surfaces a clear "not yet available" message instead of failing
        silently."""
        self.oauth_status = "unavailable"
        self.oauth_error = (
            "Google sign-in is being wired up. In the meantime, you can "
            "preview the chat experience without an account."
        )

    @rx.event
    def clear_oauth_error(self):
        self.oauth_status = "idle"
        self.oauth_error = ""

    @rx.event
    def sign_out(self):
        self.user_email = ""
        self.user_name = ""
        self.user_picture = ""
        self.is_authenticated = False
        self.oauth_status = "idle"
        self.oauth_error = ""
        return rx.redirect("/")
