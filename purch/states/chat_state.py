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

import asyncio
import logging
import os
import time
from datetime import datetime
from typing import TypedDict

import reflex as rx

from purch import backend, wallet_backend, wallet_intent
from purch.errors import safe_banner_message, safe_error_message
from purch.states.sidebar_state import SidebarState
from purch.time_utils import now_display


class WalletChoice(TypedDict):
    id: int
    name: str
    wallet_type: str
    balance_display: str


class ChatMessage(TypedDict):
    role: str  # "user" | "assistant"
    text: str
    meta: str
    time: str
    alert: str  # "" | "warning" | "danger"


# Default suggestions shown in the empty chat state. They deliberately
# include a wallet name so it's obvious a purchase can name its wallet,
# plus the borrowed / lent wordings that now persist to a wallet.
PROMPT_CHIPS: list[str] = [
    "milk tea 85 gcash",
    "grab ride 240 cash",
    "borrowed 250 from Aivann",
    "lent 300 to Maria",
    "how much this week?",
    "set food budget to 3000",
]


def _now_str(timezone_name: str = "") -> str:
    return now_display(timezone_name)


class ChatState(rx.State):
    messages: list[ChatMessage] = []
    draft: str = ""
    draft_version: int = 0
    # Suggestion chips for the empty state — rebuilt on load and after a
    # clear so they reference the user's real wallet nicknames.
    prompt_chips: list[str] = PROMPT_CHIPS.copy()

    is_sending: bool = False
    error_text: str = ""
    # Bumped every time a new banner is raised so a stale auto-dismiss
    # timer can never clear a newer message.
    error_token: int = 0
    confirm_clear: bool = False

    # Carried across turns so multi-step flows (edit confirm, currency
    # conversion) survive re-render — identical shape to what the
    # Streamlit shell uses in st.session_state.
    pending_edit: dict[str, str | int | float] = {}
    pending_conversion: dict[str, str | int | float] = {}

    # Wallet follow-up: when a purchase is logged without a wallet, we
    # park it here and render clickable wallet chips instead of asking
    # the user to type (and possibly misspell) a wallet name.
    pending_wallet: dict[str, str | int | float] = {}
    wallet_choices: list[WalletChoice] = []
    # Explicit latch so the "a wallet must be picked" requirement survives
    # any re-mount, state rehydration, or partially-populated instance.
    awaiting_wallet: bool = False

    # Last transaction written this turn — used for wallet linking.
    _last_tx: dict[str, str | int | float] = {}

    # Simple rolling rate limit — same intent as the Streamlit version.
    _req_count: int = 0
    _req_window_start: float = 0.0
    timezone_name: str = ""

    @rx.var
    def has_messages(self) -> bool:
        return len(self.messages) > 0

    @rx.var
    def has_wallet_choices(self) -> bool:
        return len(self.wallet_choices) > 0 or self.awaiting_wallet

    def _pending_wallet_snapshot(self) -> dict[str, str | int | float]:
        """Read the parked purchase defensively.

        Reflex may hand us an instance where the field was seeded directly
        (constructor kwargs, rehydration) without going through the normal
        descriptor path, so fall back to the raw instance dict."""
        pending = self.pending_wallet
        if not pending:
            raw = self.__dict__.get("pending_wallet")
            if isinstance(raw, dict) and raw:
                return dict(raw)
            return {}
        return dict(pending)

    def _pending_wallet_choices(self) -> list[WalletChoice]:
        choices = self.wallet_choices
        if not choices:
            raw = self.__dict__.get("wallet_choices")
            if isinstance(raw, list) and raw:
                return list(raw)
            return []
        return list(choices)

    def _wallet_selection_required(self) -> bool:
        """True while the previous purchase still needs a wallet. Checks the
        parked purchase, the rendered chips, AND the explicit latch so no
        single dropped field can let a message slip through."""
        return bool(
            self._pending_wallet_snapshot()
            or self._pending_wallet_choices()
            or self.__dict__.get("awaiting_wallet")
            or self.awaiting_wallet
        )

    @rx.var
    def message_count(self) -> int:
        return len(self.messages)

    @rx.event
    async def on_load(self):
        """Best-effort DB bootstrap on mount for authenticated users. When
        no identity is active this is a no-op — the page renders a
        sign-in prompt instead of the composer, so there's nothing to
        bootstrap for."""
        try:
            user_id = await self._user_id()
            if not user_id:
                return
            backend.bootstrap()
            backend.ensure_user(user_id)
        except Exception as e:
            logging.exception(f"Chat on_load failed: {e}")
        yield ChatState.refresh_prompt_chips

    async def _user_id(self) -> str:
        """Resolve the current user id from AuthState. Returns an empty
        string when no account is active — there is no shared anonymous
        fallback: callers must gate all reads/writes on this being
        non-empty."""
        try:
            from purch.states.auth_state import AuthState

            auth = await self.get_state(AuthState)
            return auth.user_email or ""
        except Exception as e:
            logging.exception(f"user_id resolution failed: {e}")
            return ""

    def _ensure_ready(self, user_id: str) -> bool:
        """Prepare the backend without allowing setup errors to escape the event."""
        try:
            backend.bootstrap()
            backend.ensure_user(user_id)
            return True
        except Exception as e:
            logging.exception(f"Chat bootstrap failed: {e}")
            return False

    def _append_assistant_message(self, text: str, meta: str = "") -> None:
        self.messages.append(
            ChatMessage(
                role="assistant",
                text=text,
                meta=meta,
                time=_now_str(self.timezone_name),
                alert=backend.classify_alert(text),
            )
        )

    @rx.event
    def set_timezone(self, timezone_name: str):
        self.timezone_name = timezone_name.strip()

    @rx.event
    def dismiss_error(self):
        self.error_text = ""
        self.error_token += 1

    @rx.event(background=True)
    async def auto_dismiss_error(self):
        """Clear the banner 5 seconds after it was raised, unless the user
        already dismissed it or a newer banner replaced it."""
        async with self:
            token = self.error_token
        await asyncio.sleep(5)
        async with self:
            if self.error_token == token:
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
    async def confirm_clear_chat(self):
        self.messages = []
        self.confirm_clear = False
        self.error_text = ""
        self.pending_edit = {}
        self.pending_conversion = {}
        self.pending_wallet = {}
        self.wallet_choices = []
        self.awaiting_wallet = False
        self.draft = ""
        self.draft_version += 1
        yield ChatState.refresh_prompt_chips

    # ------------------------------------------------------------------ #
    # Prompt suggestions
    # ------------------------------------------------------------------ #

    def _build_prompt_chips(self, wallets: list[dict]) -> list[str]:
        """Suggestions that name the user's own wallets when we have them,
        so the required wallet step is obvious from the first message."""
        names = [
            str(w["name"])
            for w in wallet_backend.consumable_wallets(wallets)
            if str(w["name"]).strip()
        ]
        chips: list[str] = []
        if names:
            first = names[0]
            second = names[1] if len(names) > 1 else first
            chips.append(f"milk tea 85 {first}")
            chips.append(f"grab ride 240 {second}")
            chips.append(f"how much is left in {first}?")
        else:
            chips.append("milk tea 85 gcash")
            chips.append("grab ride 240 cash")
            chips.append("how much this week?")
        chips.append("borrowed 250 from Aivann")
        chips.append("lent 300 to Maria")
        chips.append("set food budget to 3000")
        return chips

    @rx.event
    async def refresh_prompt_chips(self):
        """Rebuild the empty-state suggestions from the user's wallets."""
        try:
            user_id = await self._user_id()
            if not user_id:
                self.prompt_chips = list(PROMPT_CHIPS)
                return
            wallets = await asyncio.to_thread(self._wallet_rows, user_id)
            self.prompt_chips = self._build_prompt_chips(wallets)
        except Exception as e:
            logging.exception(f"prompt chip refresh failed: {e}")
            self.prompt_chips = list(PROMPT_CHIPS)

    # ------------------------------------------------------------------ #
    # Wallet helpers
    # ------------------------------------------------------------------ #

    def _wallet_rows(self, user_id: str) -> list[dict]:
        try:
            if not wallet_backend.available():
                return []
            return wallet_backend.list_wallets(user_id)
        except Exception as e:
            logging.exception(f"wallet lookup failed: {e}")
            return []

    def _wallet_query_reply(self, user_id: str, prompt: str) -> str:
        """Answer a wallet balance/allowance question straight from the
        wallet tables. Returns "" when the message isn't a wallet
        question (the agent then handles it as usual)."""
        if self.pending_conversion or self.pending_edit:
            return ""
        low = prompt.lower().strip()
        if not low:
            return ""

        wallets = self._wallet_rows(user_id)
        if not wallets:
            return ""

        wallet_words = ["wallet", "wallets", "allowance", "balance", "funds"]
        for keywords in wallet_backend.TYPE_KEYWORDS.values():
            wallet_words.extend(keywords)
        wallet_words.extend(w["name"].lower() for w in wallets)
        if not any(word and word in low for word in wallet_words):
            return ""

        question_markers = (
            "how much",
            "how many",
            "left",
            "remaining",
            "balance",
            "allowance",
            "show",
            "list",
            "what's in",
            "whats in",
            "do i have",
            "available",
            "?",
        )
        if not any(marker in low for marker in question_markers):
            return ""

        try:
            from purch import wallet_llm

            parsed = wallet_llm.extract_wallet_query(prompt)
        except Exception as e:
            logging.exception(f"wallet query classification failed: {e}")
            parsed = {
                "is_wallet_question": True,
                "wallet_hint": "",
                "query_type": "list",
            }
        if not parsed.get("is_wallet_question"):
            return ""

        hint = str(parsed.get("wallet_hint") or "")
        match = wallet_backend.match_wallet(
            wallets, hint
        ) or wallet_backend.detect_wallet_in_text(wallets, prompt)

        if match and parsed.get("query_type") != "list":
            amount = wallet_backend.money(match["balance"])
            if match["wallet_type"] in ("Debt", "Loan"):
                return (
                    f"{match['name']} ({match['wallet_type']}) is at "
                    f"₱{amount} outstanding."
                )
            return (
                f"{match['name']} ({match['wallet_type']}) has ₱{amount} "
                "available right now."
            )

        lines = [
            f"- {w['name']} ({w['wallet_type']}): "
            f"₱{wallet_backend.money(w['balance'])}"
            for w in wallets
        ]
        totals = wallet_backend.summary(wallets)
        return (
            "Here's where your money sits:\n"
            + "\n".join(lines)
            + f"\n\nSpendable total: ₱{wallet_backend.money(totals['assets'])}"
        )

    def _debt_intent_reply(self, user_id: str, prompt: str) -> str:
        """Handle borrowed / lent messages BEFORE the generic transaction
        extractor so a debt is never mislogged as spending.

        Creates the named Borrowed (`Debt`) / `Lent` wallet when it's new,
        adds to it when it already exists, and writes a ledger entry each
        time. Returns "" when the message isn't a debt/lent message.
        """
        if self.pending_conversion or self.pending_edit:
            return ""

        parsed = wallet_intent.parse_debt_message(prompt)
        if parsed is None:
            return ""

        direction = str(parsed["direction"])
        amount = float(parsed["amount"] or 0)
        person = str(parsed["person"] or "")

        # Fall back to the LLM only when the cheap parse left a gap.
        if not person or amount <= 0:
            try:
                from purch import wallet_llm

                details = wallet_llm.extract_debt_details(prompt)
            except Exception as e:
                logging.exception(f"debt detail fallback failed: {e}")
                details = {}
            if details.get("is_debt_message"):
                if not person:
                    person = str(details.get("person") or "")
                if amount <= 0:
                    amount = float(details.get("amount") or 0)
                llm_direction = str(details.get("direction") or "none")
                if llm_direction in ("borrowed", "lent"):
                    direction = llm_direction

        label = wallet_intent.label_for(direction)
        if amount <= 0:
            who = (
                f" from {person}"
                if direction == "borrowed" and person
                else (f" to {person}" if person else "")
            )
            example = person or (
                "Aivann" if direction == "borrowed" else "Maria"
            )
            preposition = "from" if direction == "borrowed" else "to"
            return (
                f"How much did you {label.lower()}{who}? Say something like "
                f"'{label.lower()} 250 {preposition} {example}' and I'll "
                "track it in a wallet for you."
            )

        if not wallet_backend.available():
            return (
                "I couldn't reach your wallets just now, so I didn't record "
                "that. Please try again in a moment."
            )

        wallet_type = wallet_intent.wallet_type_for(direction)
        wallet_name = person or wallet_intent.default_name_for(direction)
        description = wallet_intent.ledger_description(direction, person)

        try:
            wallet = wallet_backend.upsert_debt_wallet(
                user_id,
                wallet_name,
                wallet_type,
                amount,
                description,
            )
        except Exception as e:
            logging.exception(f"debt wallet upsert failed: {e}")
            wallet = None

        if wallet is None:
            return (
                f"I couldn't save that {label.lower()} amount to a wallet "
                "just now. Please try again in a moment."
            )

        balance = wallet_backend.money(wallet["balance"])
        moved = wallet_backend.money(amount)
        created_note = (
            f" I created a new {label} wallet for it."
            if wallet.get("created")
            else ""
        )
        if direction == "lent":
            who = f" to {person}" if person else ""
            return (
                f"🤝 Lent ₱{moved}{who} — tracked in your “{wallet['name']}” "
                f"Lent wallet.{created_note} They now owe you ₱{balance}."
            )
        who = f" from {person}" if person else ""
        return (
            f"🧾 Borrowed ₱{moved}{who} — tracked in your “{wallet['name']}” "
            f"Borrowed wallet.{created_note} Outstanding: ₱{balance}."
        )

    def _wallet_choice_payload(self, wallets: list[dict]) -> list[WalletChoice]:
        return [
            WalletChoice(
                id=int(w["id"]),
                name=str(w["name"]),
                wallet_type=str(w["wallet_type"]),
                balance_display=wallet_backend.money(w["balance"]),
            )
            for w in wallets
        ]

    async def _apply_wallet_for_last_tx(self, user_id: str, prompt: str) -> str:
        """Link the transaction just written to a wallet.

        If the message named a wallet (by nickname or a money-source word
        like cash / bank / savings) we subtract immediately and write the
        ledger entry. Otherwise we park the transaction and surface
        clickable wallet chips so the user never has to type a name.
        """
        tx = dict(self._last_tx)
        self._last_tx = {}
        if not tx:
            return ""

        wallets = await asyncio.to_thread(self._wallet_rows, user_id)
        if not wallets:
            return ""

        amount = float(tx.get("amount") or 0)
        item = str(tx.get("item") or "purchase")
        tx_id = int(tx.get("transaction_id") or 0)

        match = wallet_backend.detect_wallet_in_text(wallets, prompt)
        if match is None:
            try:
                from purch import wallet_llm

                hint = await asyncio.to_thread(
                    wallet_llm.extract_wallet_reference, prompt
                )
            except Exception as e:
                logging.exception(f"wallet reference lookup failed: {e}")
                hint = ""
            if hint:
                match = wallet_backend.match_wallet(wallets, hint)

        if match is not None:
            updated = await asyncio.to_thread(
                wallet_backend.apply_purchase,
                user_id,
                int(match["id"]),
                amount,
                item,
                tx_id or None,
            )
            if updated is not None:
                self.pending_wallet = {}
                self.wallet_choices = []
                self.awaiting_wallet = False
                return (
                    f"💰 Taken from {updated['name']} — ₱"
                    f"{wallet_backend.money(updated['balance'])} left."
                )

        self.pending_wallet = {
            "transaction_id": tx_id,
            "amount": amount,
            "item": item,
        }
        self.wallet_choices = self._wallet_choice_payload(wallets)
        self.awaiting_wallet = True
        return (
            "Which wallet did this come from? Tap one below to finish "
            "logging it — a wallet is required."
        )

    @rx.event
    async def choose_wallet(self, wallet_id: int):
        """Apply the parked transaction to the tapped wallet."""
        pending = self._pending_wallet_snapshot()
        if not pending:
            self.wallet_choices = []
            self.awaiting_wallet = False
            return
        user_id = await self._user_id()
        if not user_id:
            self.error_text = "Sign in again to update a wallet."
            self.error_token += 1
            yield ChatState.auto_dismiss_error
            return
        try:
            updated = await asyncio.to_thread(
                wallet_backend.apply_purchase,
                user_id,
                int(wallet_id),
                float(pending.get("amount") or 0),
                pending.get("item") or "purchase",
                int(pending.get("transaction_id") or 0) or None,
            )
        except Exception as e:
            logging.exception(f"wallet apply failed: {e}")
            updated = None

        self.pending_wallet = {}
        self.wallet_choices = []
        self.awaiting_wallet = False
        if updated is None:
            # Keep the requirement intact: restore the pending purchase and
            # the choice buttons so the user can retry.
            self.pending_wallet = dict(pending)
            self.wallet_choices = self._wallet_choice_payload(
                self._wallet_rows(user_id)
            )
            self.awaiting_wallet = True
            self._append_assistant_message(
                "I couldn't update that wallet just now — please pick one "
                "again."
            )
            return
        self._append_assistant_message(
            f"💰 Logged against {updated['name']} — ₱"
            f"{wallet_backend.money(updated['balance'])} left."
        )
        yield SidebarState.refresh

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
    ) -> tuple[str, str, bool] | None:
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
            tx_id = backend.insert_transaction(
                user_id, prompt, item, php_amount, category
            )
            self._last_tx = {
                "transaction_id": int(tx_id or 0),
                "amount": php_amount,
                "item": item,
            }
            tone = backend.get_user_tone(user_id)
            try:
                comment = backend.generate_comment(
                    item, php_amount, category, "PHP", tone
                )
            except Exception as e:
                logging.exception(f"Comment generation failed: {e}")
                comment = ""
            self.pending_conversion = {}
            response = f"Logged: {item} — ₱{php_amount:.2f} ({category})"
            if comment:
                response += f"\n\n{comment}"
            return response, f"{category} • ₱{php_amount:.0f} • Today", False
        except Exception as e:
            logging.exception(f"Conversion insert failed: {e}")
            return safe_error_message(e), "", True

    def _handle_pending_edit(self, prompt: str) -> tuple[str, str, bool] | None:
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
                return "Deleted.", "", False
            new_amount = edit.get("new_amount")
            new_category = edit.get("new_category")
            backend.update_transaction(
                tx_id,
                amount=float(new_amount) if new_amount else None,
                category=str(new_category) if new_category else None,
            )
            self.pending_edit = {}
            return "Updated!", "", False
        except Exception as e:
            logging.exception(f"Edit confirm failed: {e}")
            return safe_error_message(e), "", True

    @rx.event
    async def send_message(self, form_data: dict[str, str]):
        # HARD GATE: a wallet must be chosen for the previous purchase
        # before ANY new message is accepted. This runs before the draft is
        # read or cleared, before any bubble is appended, and before any
        # agent / LLM / database work — nothing is processed and nothing
        # the user typed is lost.
        if self._wallet_selection_required():
            # Re-assert the requirement on state (in case a field was
            # dropped) and keep the chips visible. NEVER clear the parked
            # purchase, the chips, the messages, or the draft here.
            pending = self._pending_wallet_snapshot()
            if pending:
                self.pending_wallet = pending
            self.awaiting_wallet = True
            choices = self._pending_wallet_choices()
            if not choices:
                user_id = await self._user_id()
                if user_id:
                    wallets = await asyncio.to_thread(
                        self._wallet_rows, user_id
                    )
                    choices = self._wallet_choice_payload(wallets)
            self.wallet_choices = choices
            self.error_text = (
                "Pick a wallet for your last purchase first — tap one of "
                "the wallet buttons above."
            )
            self.error_token += 1
            yield ChatState.auto_dismiss_error
            return

        prompt = (form_data.get("draft") or self.draft or "").strip()
        if not prompt:
            self.error_text = "Type something first — even 'coffee 150' works."
            self.error_token += 1
            yield ChatState.auto_dismiss_error
            return

        if self.is_sending:
            return

        now = _now_str(self.timezone_name)
        user_id = await self._user_id()

        # Identity gate — no anonymous writes. If the user isn't signed
        # in we surface an inline prompt and short-circuit before we
        # touch the agent, the LLM, or the database.
        if not user_id:
            self.error_text = (
                "Sign in or continue as a guest to start logging purchases."
            )
            self.error_token += 1
            yield ChatState.auto_dismiss_error
            return

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
        yield  # flush the user message + pending indicator

        response_text = ""
        meta = ""
        fatal_error = False

        try:
            if self._rate_limited():
                rate_error = RuntimeError("rate limit")
                response_text = safe_error_message(rate_error)
                self.error_text = safe_banner_message(rate_error)
                fatal_error = True
            elif not self._ensure_ready(user_id):
                db_error = RuntimeError("database unavailable")
                response_text = safe_error_message(db_error)
                self.error_text = safe_banner_message(db_error)
                fatal_error = True
            elif (
                not (os.getenv("GROQ_API_KEY") or "").strip()
                and not self.pending_conversion
                and not self.pending_edit
            ):
                credentials_error = RuntimeError("credentials unavailable")
                response_text = safe_error_message(credentials_error)
                self.error_text = safe_banner_message(credentials_error)
                fatal_error = True
            else:
                # Borrowed / lent intent runs FIRST so debts are persisted
                # to a wallet instead of being mislogged as spending by
                # the generic transaction extractor.
                debt_answer = await asyncio.to_thread(
                    self._debt_intent_reply, user_id, prompt
                )
                # Wallet balance / allowance question — answered directly
                # from the wallet tables, no agent round-trip needed.
                wallet_answer = (
                    ""
                    if debt_answer
                    else await asyncio.to_thread(
                        self._wallet_query_reply, user_id, prompt
                    )
                )
                # Pending-conversion path (numeric PHP reply after a USD extract).
                conv_reply = (
                    None
                    if (debt_answer or wallet_answer)
                    else self._handle_pending_conversion(prompt, user_id)
                )
                if debt_answer:
                    response_text = debt_answer
                elif wallet_answer:
                    response_text = wallet_answer
                elif conv_reply is not None:
                    response_text, meta, fatal_error = conv_reply
                else:
                    # Pending-edit confirmation path.
                    edit_reply = self._handle_pending_edit(prompt)
                    if edit_reply is not None:
                        response_text, meta, fatal_error = edit_reply
                    else:
                        # Full agent round-trip.
                        result = await asyncio.to_thread(
                            backend.run_agent, user_id, prompt
                        )
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
                                "new_category": str(
                                    pe.get("new_category") or ""
                                ),
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
                            self._last_tx = {
                                "transaction_id": int(
                                    result["transaction_id"] or 0
                                ),
                                "amount": float(result["amount"]),
                                "item": str(result.get("item") or "purchase"),
                            }
        except Exception as e:
            logging.exception(f"send_message failed: {e}")
            response_text = safe_error_message(e)
            self.error_text = safe_banner_message(e)
            fatal_error = True

        # Every post-user branch reaches this single finalization point. This
        # prevents duplicate assistant bubbles and guarantees the event cannot
        # leave the websocket in a sending state after a provider or DB error.
        if not response_text:
            empty_error = RuntimeError("empty response")
            response_text = safe_error_message(empty_error)
            self.error_text = safe_banner_message(empty_error)
            fatal_error = True
        if not self.error_text:
            self.error_text = (
                ""
                if not fatal_error
                else safe_banner_message(RuntimeError("request failed"))
            )

        # Wallet linking: subtract from the named wallet, or park the
        # transaction and offer wallet chips.
        if not fatal_error and self._last_tx:
            try:
                wallet_note = await self._apply_wallet_for_last_tx(
                    user_id, prompt
                )
            except Exception as e:
                logging.exception(f"wallet linking failed: {e}")
                wallet_note = ""
            if wallet_note:
                response_text = f"{response_text}\n\n{wallet_note}"

        self._append_assistant_message(response_text, meta)
        self.is_sending = False

        if self.error_text:
            self.error_token += 1
            yield ChatState.auto_dismiss_error

        # Pending edit/conversion state is changed only by successful handling
        # or by an agent response that explicitly creates a pending action.
        if fatal_error:
            return
        yield SidebarState.refresh
        yield ChatState.refresh_prompt_chips
