"""Auth state — real sign-in, sign-up, guest, and Google OAuth flows.

Three account paths are supported end-to-end:

1. **Google** via Supabase — `begin_google_login` asks Supabase for the
   provider's authorize URL and `rx.redirect`s to it. When the user
   returns to `/login?code=...`, `handle_oauth_callback` exchanges the
   code for a Supabase session and persists the identity.
2. **Email + password** — `submit_credentials` calls either
   `sign_up_with_password` or `sign_in_with_password` depending on the
   current form mode. Both paths land in the same session-persist step.
3. **Guest** — `sign_in_as_guest` mints a fresh UUID-based identifier
   and stores it locally. No Supabase user is created; guest identity is
   private to the browser it was created in, and there is no shared
   anonymous fallback anywhere in the app.

Identity is persisted with `rx.LocalStorage` so a refresh doesn't sign
the user out. The identifier stored in `user_email` is the same string
`db.models.ensure_user(user_id)` expects — for guests we use a
`guest-<uuid>@purch.local` shape so downstream code doesn't have to
branch on account type.
"""

from __future__ import annotations

import logging
import os
import re
import uuid

import reflex as rx

from purch import backend
from purch.supabase_auth import (
    build_google_oauth_url,
    exchange_code_for_session,
    is_configured,
    safe_auth_error,
    sign_in_with_password,
    sign_up_with_password,
)
from purch.theme import ROUTES


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _sandbox_fallback_url() -> str:
    """Fallback redirect target when we can't derive an origin from the
    request. Prefers an explicit env var; otherwise uses the sandbox URL
    that was probed at build time."""
    env = os.getenv("PURCH_OAUTH_REDIRECT_URL", "").strip()
    if env:
        return env
    return (
        "https://8080-10ab0098-f3e4-4a14-8799-57149687e2ba"
        ".build.reflexsandbox.com/login"
    )


class AuthState(rx.State):
    # Persisted identity — LocalStorage keeps the user signed in across
    # tabs and refreshes without needing a server-side session store.
    user_id: str = rx.LocalStorage("", name="purch_user_id")
    user_email: str = rx.LocalStorage("", name="purch_user_email")
    user_name: str = rx.LocalStorage("", name="purch_user_name")
    user_picture: str = rx.LocalStorage("", name="purch_user_picture")
    auth_method: str = rx.LocalStorage("", name="purch_auth_method")

    # Form + UI state — plain state so it resets naturally on refresh.
    mode: str = "signin"  # "signin" | "signup"
    email_input: str = ""
    password_input: str = ""
    name_input: str = ""

    status: str = "idle"  # idle | busy | error | success
    error_text: str = ""
    info_text: str = ""

    # Legacy fields kept because other pages already read them.
    oauth_status: str = "idle"
    oauth_error: str = ""

    # ------------------------------------------------------------------ #
    # Computed
    # ------------------------------------------------------------------ #

    @rx.var
    def is_authenticated(self) -> bool:
        return bool(self.user_email)

    @rx.var
    def display_name(self) -> str:
        if self.user_name:
            return self.user_name
        if self.user_email and "@" in self.user_email:
            local = self.user_email.split("@", 1)[0]
            if local.startswith("guest-"):
                return "Guest"
            return local
        return "Guest"

    @rx.var
    def is_guest(self) -> bool:
        return self.auth_method == "guest"

    @rx.var
    def is_busy(self) -> bool:
        return self.status == "busy"

    @rx.var
    def is_signup_mode(self) -> bool:
        return self.mode == "signup"

    @rx.var
    def submit_label(self) -> str:
        if self.is_busy:
            return "Please wait…"
        return "Create account" if self.mode == "signup" else "Sign in"

    @rx.var
    def toggle_prompt(self) -> str:
        return (
            "Already have an account? Sign in"
            if self.mode == "signup"
            else "New to Purch? Create an account"
        )

    # ------------------------------------------------------------------ #
    # Form field events
    # ------------------------------------------------------------------ #

    @rx.event
    def set_email(self, value: str):
        self.email_input = value

    @rx.event
    def set_password(self, value: str):
        self.password_input = value

    @rx.event
    def set_name(self, value: str):
        self.name_input = value

    @rx.event
    def toggle_mode(self):
        self.mode = "signin" if self.mode == "signup" else "signup"
        self.error_text = ""
        self.info_text = ""
        self.status = "idle"

    @rx.event
    def dismiss_message(self):
        self.error_text = ""
        self.info_text = ""
        self.status = "idle"

    # ------------------------------------------------------------------ #
    # Guest sign-in
    # ------------------------------------------------------------------ #

    @rx.event
    def sign_in_as_guest(self):
        """Create a fresh browser-local guest identity. Each click mints
        a new UUID — there is no shared 'anonymous' user any more."""
        try:
            guest_uuid = uuid.uuid4().hex[:12]
            guest_email = f"guest-{guest_uuid}@purch.local"
            guest_name = f"Guest {guest_uuid[:6]}"
            self._persist_identity(
                user_id=guest_email,
                email=guest_email,
                name=guest_name,
                picture="",
                method="guest",
            )
            self.info_text = (
                "Signed in as guest — your data stays on this device."
            )
            self.status = "success"
            return rx.redirect(ROUTES["chat"])
        except Exception as e:
            logging.exception(f"Guest sign-in failed: {e}")
            self._show_error(
                "Couldn't start a guest session. Please try again."
            )

    # ------------------------------------------------------------------ #
    # Email + password
    # ------------------------------------------------------------------ #

    @rx.event
    def submit_credentials(self, form_data: dict[str, str]):
        """Handle both sign-in and sign-up from the same form."""
        if not is_configured():
            self._show_error(
                "Email sign-in isn't available right now. "
                "Try guest access to preview Purch."
            )
            return

        email = (form_data.get("email") or self.email_input or "").strip()
        password = form_data.get("password") or self.password_input or ""
        name = (form_data.get("name") or self.name_input or "").strip()

        if not _EMAIL_RE.match(email):
            self._show_error("Please enter a valid email address.")
            return
        if len(password) < 6:
            self._show_error("Password needs to be at least 6 characters long.")
            return

        self.status = "busy"
        self.error_text = ""
        self.info_text = ""
        yield

        try:
            if self.mode == "signup":
                result = sign_up_with_password(email, password, name or None)
                # Supabase may require email confirmation depending on
                # project settings; treat "no session yet" as a helpful
                # notice rather than an error.
                if not result.get("user_id"):
                    self.info_text = (
                        "Check your inbox to confirm your email, then sign in."
                    )
                    self.status = "success"
                    self.mode = "signin"
                    return
            else:
                result = sign_in_with_password(email, password)

            self._persist_identity(
                user_id=result["user_id"],
                email=result["email"] or email,
                name=result["name"] or name,
                picture="",
                method="email",
            )
            self.info_text = "Signed in — taking you to the chat."
            self.status = "success"
            self.password_input = ""
            yield rx.redirect(ROUTES["chat"])
        except Exception as e:
            logging.exception(f"Email auth failed: {e}")
            self._show_error(safe_auth_error(e))

    # ------------------------------------------------------------------ #
    # Google OAuth
    # ------------------------------------------------------------------ #

    @rx.event
    def begin_google_login(self):
        """Redirect the browser to Supabase's Google authorize endpoint."""
        if not is_configured():
            self._show_error(
                "Google sign-in isn't available right now. "
                "Try guest access to preview Purch."
            )
            return

        redirect_to = self._compute_redirect_url()
        self.status = "busy"
        self.error_text = ""
        self.info_text = "Redirecting to Google…"
        self.oauth_status = "redirecting"
        yield

        try:
            oauth_url = build_google_oauth_url(redirect_to)
            return rx.redirect(oauth_url)
        except Exception as e:
            logging.exception(f"Google OAuth start failed: {e}")
            self.oauth_status = "error"
            self._show_error(safe_auth_error(e))

    @rx.event
    def handle_oauth_callback(self):
        """Runs on `/login` mount. If Supabase has redirected us back
        with a `?code=...`, complete the exchange and persist the
        session. Silent no-op when there's no code — safe to attach to
        every login page load."""
        try:
            params = self.router.url.query_parameters or {}
        except Exception:
            logging.exception("Unexpected error reading query params")
            params = {}
        code = params.get("code") or ""
        oauth_error = params.get("error_description") or params.get("error")

        if oauth_error:
            self._show_error(safe_auth_error(RuntimeError(oauth_error)))
            return

        if not code:
            return

        self.status = "busy"
        self.error_text = ""
        self.info_text = "Finishing Google sign-in…"
        yield

        try:
            result = exchange_code_for_session(code)
            self._persist_identity(
                user_id=result["user_id"],
                email=result["email"],
                name=result["name"],
                picture="",
                method="google",
            )
            self.info_text = "Signed in with Google — taking you to the chat."
            self.status = "success"
            yield rx.redirect(ROUTES["chat"])
        except Exception as e:
            logging.exception(f"OAuth exchange failed: {e}")
            self._show_error(safe_auth_error(e))

    # ------------------------------------------------------------------ #
    # Session control
    # ------------------------------------------------------------------ #

    @rx.event
    def sign_out(self):
        self.user_id = ""
        self.user_email = ""
        self.user_name = ""
        self.user_picture = ""
        self.auth_method = ""
        self.status = "idle"
        self.error_text = ""
        self.info_text = ""
        self.oauth_status = "idle"
        self.oauth_error = ""
        self.email_input = ""
        self.password_input = ""
        self.name_input = ""
        return rx.redirect(ROUTES["login"])

    @rx.event
    def clear_oauth_error(self):
        """Kept for backward compatibility with the older login page."""
        self.oauth_status = "idle"
        self.oauth_error = ""
        self.error_text = ""
        self.info_text = ""
        self.status = "idle"

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _persist_identity(
        self,
        user_id: str,
        email: str,
        name: str,
        picture: str,
        method: str,
    ) -> None:
        self.user_id = user_id or email
        self.user_email = email or user_id
        self.user_name = name or ""
        self.user_picture = picture or ""
        self.auth_method = method
        try:
            backend.bootstrap()
            backend.ensure_user(self.user_email)
        except Exception as e:
            logging.exception(f"ensure_user after sign-in failed: {e}")

    def _show_error(self, message: str) -> None:
        self.error_text = message
        self.info_text = ""
        self.status = "error"

    def _compute_redirect_url(self) -> str:
        """Best-effort origin detection for the OAuth `redirect_to`.
        Falls back to the sandbox/env URL if we can't build one from the
        current request."""
        try:
            page = self.router.page
            host = getattr(page, "host", "") or ""
            if host:
                base = host.rstrip("/")
                if not base.startswith("http"):
                    base = f"https://{base}"
                return f"{base}{ROUTES['login']}"
        except Exception:
            logging.exception("Unexpected error deriving redirect origin")
        return _sandbox_fallback_url()
