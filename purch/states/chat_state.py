"""Chat state — wired to the real LangGraph agent + SQLite backend.

Message flow (mirrors the Streamlit `handle_user_input` in `app.py`):

1.  If a currency conversion is pending and the user replied with a
    number, insert the transaction directly (no agent round-trip needed).
2.  If an edit is pending and the user confirmed, apply the update or
    delete against the DB.
3.  Otherwise, hand the message to `agent.graph.run_agent`, propagate any
    `pending_edit` / `pending_conversion` it returns, and render the
    assistant response with an alert border classification and — when a
    transaction was actually written — a receipt meta line.

The database and business logic are imported via `purch.backend`, which
re-exports the root `agent/`, `llm/`, `db/` packages under a normalized
namespace so nothing in the Streamlit fallback has to change.
"""

import logging
import time
from datetime import datetime
from typing import TypedDict

import reflex as rx

from purch import backend
from purch.states.sidebar_state import ANON_USER, SidebarState


class ChatMessage(TypedDict):
    role: str  # "user" | "assistant"
    text: str
    meta: str
    time: str
    alert: str  # "" | "warning" | "danger"


PROMPT_CHIPS: list[str] = [
    "milk tea ₱85",
    "grab ride 240",
    "how much this week?",
    "set food budget to 3000",
]


def _now_str() -> str:
    return datetime.now().strftime("%I:%M %p").lstrip("0")


class ChatState(rx.State):
    messages: list[ChatMessage] = []
    draft: str = ""
    draft_version: int = 0

    is_sending: bool = False
    error_text: str = ""
    confirm_clear: bool = False

    # Carried across turns so multi-step flows (edit confirm, currency
    # conversion) survive re-render — identical shape to what the
    # Streamlit shell uses in st.session_state.
    pending_edit: dict[str, str | int | float] = {}
    pending_conversion: dict[str, str | int | float] = {}

    # Simple rolling rate limit — same intent as the Streamlit version.
    _req_count: int = 0
    _req_window_start: float = 0.0

    @rx.var
    def has_messages(self) -> bool:
        return len(self.messages) > 0

    @rx.var
    def message_count(self) -> int:
        return len(self.messages)

    @rx.event
    async def on_load(self):
        """Best-effort DB bootstrap on mount. send_message is also
        self-sufficient — it will bootstrap+ensure_user on demand — so
        the chat still works if this handler never fires."""
        try:
            backend.bootstrap()
            user_id = await self._user_id()
            backend.ensure_user(user_id)
        except Exception as e:
            logging.exception(f"Chat on_load failed: {e}")

    async def _user_id(self) -> str:
        """Resolve the current user id defensively — fall back to the
        anonymous account rather than propagating errors when the auth
        state isn't reachable (e.g. tests / non-request contexts)."""
        try:
            from purch.states.auth_state import AuthState

            auth = await self.get_state(AuthState)
            return auth.user_email or ANON_USER
        except Exception as e:
            logging.exception(f"user_id resolution failed: {e}")
            return ANON_USER

    def _ensure_ready(self, user_id: str) -> None:
        """Idempotent bootstrap so send_message never depends on on_load."""
        try:
            backend.bootstrap()
            backend.ensure_user(user_id)
        except Exception as e:
            logging.exception(f"Chat bootstrap failed: {e}")

    @rx.event
    def dismiss_error(self):
        self.error_text = ""

    @rx.event
    def use_prompt(self, prompt: str):
        self.draft = prompt
        self.draft_version += 1
        self.error_text = ""

    @rx.event
    def request_clear(self):
        self.confirm_clear = True

    @rx.event
    def cancel_clear(self):
        self.confirm_clear = False

    @rx.event
    def confirm_clear_chat(self):
        self.messages = []
        self.confirm_clear = False
        self.error_text = ""
        self.pending_edit = {}
        self.pending_conversion = {}
        self.draft = ""
        self.draft_version += 1

    def _rate_limited(self) -> bool:
        now = time.time()
        if now - self._req_window_start > 60:
            self._req_count = 0
            self._req_window_start = now
        if self._req_count >= 25:
            return True
        self._req_count += 1
        return False

    def _handle_pending_conversion(
        self, prompt: str, user_id: str
    ) -> tuple[str, str] | None:
        conv = self.pending_conversion
        if not conv:
            return None
        try:
            php_amount = float(prompt.strip().replace(",", ""))
        except ValueError:
            return None
        if php_amount <= 0:
            return None
        try:
            item = str(conv.get("item", ""))
            category = str(conv.get("category", "Other"))
            backend.insert_transaction(
                user_id, prompt, item, php_amount, category
            )
            tone = backend.get_user_tone(user_id)
            try:
                comment = backend.generate_comment(
                    item, php_amount, category, "PHP", tone
                )
            except Exception:
                logging.exception("Unexpected error")
                comment = ""
            self.pending_conversion = {}
            response = f"Logged: {item} — ₱{php_amount:.2f} ({category})"
            if comment:
                response += f"\n\n{comment}"
            return response, f"{category} • ₱{php_amount:.0f} • Today"
        except Exception as e:
            logging.exception(f"Conversion insert failed: {e}")
            return f"Couldn't log that: {e}", ""

    def _handle_pending_edit(self, prompt: str) -> tuple[str, str] | None:
        edit = self.pending_edit
        if not edit:
            return None
        if prompt.strip().lower() not in ("yes", "y", "confirm", "yep", "sure"):
            return None
        try:
            tx_id = int(edit.get("transaction_id", 0))
            if edit.get("action") == "delete":
                backend.delete_transaction(tx_id)
                self.pending_edit = {}
                return "Deleted.", ""
            new_amount = edit.get("new_amount")
            new_category = edit.get("new_category")
            backend.update_transaction(
                tx_id,
                amount=float(new_amount) if new_amount else None,
                category=str(new_category) if new_category else None,
            )
            self.pending_edit = {}
            return "Updated!", ""
        except Exception as e:
            logging.exception(f"Edit confirm failed: {e}")
            return f"Couldn't apply that change: {e}", ""

    @rx.event
    async def send_message(self, form_data: dict[str, str]):
        prompt = (form_data.get("draft") or self.draft or "").strip()
        if not prompt:
            self.error_text = "Type something first — even 'coffee 150' works."
            return

        if self.is_sending:
            return

        if self._rate_limited():
            self.error_text = (
                "Slow down a second — you've sent a lot of messages very "
                "quickly. Try again in a minute."
            )
            return

        now = _now_str()
        user_id = await self._user_id()
        self._ensure_ready(user_id)

        self.messages.append(
            ChatMessage(
                role="user",
                text=prompt,
                meta="",
                time=now,
                alert="",
            )
        )
        self.draft = ""
        self.draft_version += 1
        self.error_text = ""
        self.is_sending = True
        yield  # flush user message + pending indicator

        response_text = ""
        meta = ""

        try:
            # Pending-conversion path (numeric PHP reply after a USD extract)
            conv_reply = self._handle_pending_conversion(prompt, user_id)
            if conv_reply is not None:
                response_text, meta = conv_reply
            else:
                # Pending-edit confirmation path
                edit_reply = self._handle_pending_edit(prompt)
                if edit_reply is not None:
                    response_text, meta = edit_reply
                else:
                    # Full agent round-trip
                    result = backend.run_agent(user_id, prompt)
                    response_text = result.get("response") or ""
                    if result.get("pending_conversion"):
                        pc = result["pending_conversion"]
                        self.pending_conversion = {
                            "item": str(pc.get("item", "")),
                            "category": str(pc.get("category", "Other")),
                            "original_amount": float(
                                pc.get("original_amount", 0) or 0
                            ),
                            "original_currency": str(
                                pc.get("original_currency", "")
                            ),
                        }
                    if result.get("pending_edit"):
                        pe = result["pending_edit"]
                        self.pending_edit = {
                            "action": str(pe.get("action", "update")),
                            "transaction_id": int(
                                pe.get("transaction_id", 0) or 0
                            ),
                            "new_amount": float(pe.get("new_amount") or 0),
                            "new_category": str(pe.get("new_category") or ""),
                        }
                    if (
                        result.get("transaction_id")
                        and result.get("category")
                        and result.get("amount") is not None
                    ):
                        meta = (
                            f"{result['category']} • "
                            f"₱{float(result['amount']):.0f} • Today"
                        )
        except Exception as e:
            logging.exception(f"send_message failed: {e}")
            response_text = "Something went wrong on my end. Try again?"
            self.error_text = f"Backend error: {e}"

        alert = backend.classify_alert(response_text)

        self.messages.append(
            ChatMessage(
                role="assistant",
                text=response_text or "(no response)",
                meta=meta,
                time=_now_str(),
                alert=alert,
            )
        )
        self.is_sending = False

        # Refresh sidebar totals in case budgets/spending changed.
        yield SidebarState.refresh
