"""Wallet management state — create, edit, archive, and browse wallets.

All writes happen through `purch.wallet_backend`, which never touches
account numbers or any sensitive account detail: a wallet is only a
nickname, a type, a balance, and an optional note.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TypedDict

import reflex as rx

from purch import wallet_backend
from purch.wallet_backend import WALLET_TYPES


class WalletRow(TypedDict):
    id: int
    name: str
    wallet_type: str
    balance: float
    balance_display: str
    note: str
    is_archived: bool
    accent: str


class WalletState(rx.State):
    wallets: list[WalletRow] = []
    archived_wallets: list[WalletRow] = []

    wallet_types: list[str] = list(WALLET_TYPES)

    is_loading: bool = False
    has_loaded: bool = False
    unavailable: bool = False
    unauthenticated: bool = False
    error_text: str = ""
    info_text: str = ""
    # Bumped whenever a banner is raised so a stale 5s timer can never
    # clear a newer message.
    message_token: int = 0

    show_archived: bool = False

    # Form state
    form_open: bool = False
    editing_id: int = 0
    form_version: int = 0
    form_name: str = ""
    form_type: str = "Cash"
    form_balance: str = ""
    form_note: str = ""

    assets_display: str = "0.00"
    liabilities_display: str = "0.00"
    net_display: str = "0.00"

    @rx.var
    def has_wallets(self) -> bool:
        return len(self.wallets) > 0

    @rx.var
    def has_archived(self) -> bool:
        return len(self.archived_wallets) > 0

    @rx.var
    def is_editing(self) -> bool:
        return self.editing_id > 0

    @rx.var
    def form_title(self) -> str:
        return "Edit wallet" if self.editing_id > 0 else "New wallet"

    @rx.var
    def submit_label(self) -> str:
        return "Save changes" if self.editing_id > 0 else "Create wallet"

    async def _user_id(self) -> str:
        try:
            from purch.states.auth_state import AuthState

            auth = await self.get_state(AuthState)
            return auth.user_email or ""
        except Exception as e:
            logging.exception(f"wallet user lookup failed: {e}")
            return ""

    # ------------------------------------------------------------------ #
    # Loading
    # ------------------------------------------------------------------ #

    @rx.event
    async def on_load(self):
        yield WalletState.refresh

    @rx.event
    async def refresh(self):
        if self.is_loading:
            return
        self.is_loading = True
        self.error_text = ""
        yield

        try:
            if not wallet_backend.available():
                self.unavailable = True
                self.has_loaded = True
                return

            self.unavailable = False
            user_id = await self._user_id()
            if not user_id:
                self.unauthenticated = True
                self.wallets = []
                self.archived_wallets = []
                self.has_loaded = True
                return

            self.unauthenticated = False
            rows = await asyncio.to_thread(
                wallet_backend.list_wallets, user_id, True
            )
            active = [_to_row(r) for r in rows if not r["is_archived"]]
            archived = [_to_row(r) for r in rows if r["is_archived"]]
            self.wallets = active
            self.archived_wallets = archived

            totals = wallet_backend.summary(
                [r for r in rows if not r["is_archived"]]
            )
            self.assets_display = wallet_backend.money(totals["assets"])
            self.liabilities_display = wallet_backend.money(
                totals["liabilities"]
            )
            self.net_display = wallet_backend.money(totals["net"])
            self.has_loaded = True
        except Exception as e:
            logging.exception(f"wallet refresh failed: {e}")
            self.error_text = (
                "Couldn't load your wallets just now. Please try again."
            )
        finally:
            self.is_loading = False

        if self.error_text or self.info_text:
            self.message_token += 1
            yield WalletState.auto_dismiss_message

    # ------------------------------------------------------------------ #
    # Form control
    # ------------------------------------------------------------------ #

    @rx.event
    def open_create(self):
        self.form_open = True
        self.editing_id = 0
        self.form_name = ""
        self.form_type = "Cash"
        self.form_balance = ""
        self.form_note = ""
        self.form_version += 1
        self.error_text = ""
        self.info_text = ""

    @rx.event
    def open_edit(self, wallet_id: int):
        target: WalletRow | None = None
        for row in list(self.wallets) + list(self.archived_wallets):
            if int(row["id"]) == int(wallet_id):
                target = row
                break
        if target is None:
            return
        self.form_open = True
        self.editing_id = int(wallet_id)
        self.form_name = target["name"]
        self.form_type = target["wallet_type"]
        self.form_balance = f"{target['balance']:.2f}"
        self.form_note = target["note"]
        self.form_version += 1
        self.error_text = ""
        self.info_text = ""

    @rx.event
    def close_form(self):
        self.form_open = False
        self.editing_id = 0
        self.error_text = ""

    @rx.event
    def toggle_archived(self):
        self.show_archived = not self.show_archived

    @rx.event
    def dismiss_message(self):
        self.error_text = ""
        self.info_text = ""
        self.message_token += 1

    @rx.event(background=True)
    async def auto_dismiss_message(self):
        """Hide the banner after 5 seconds unless it was already dismissed
        or replaced."""
        async with self:
            token = self.message_token
        await asyncio.sleep(5)
        async with self:
            if self.message_token == token:
                self.error_text = ""
                self.info_text = ""

    # ------------------------------------------------------------------ #
    # Writes
    # ------------------------------------------------------------------ #

    @rx.event
    async def submit_wallet(self, form_data: dict[str, str]):
        self.message_token += 1
        name = (form_data.get("name") or "").strip()
        wallet_type = (form_data.get("wallet_type") or "Other").strip()
        raw_balance = (form_data.get("balance") or "0").strip()
        note = (form_data.get("note") or "").strip()

        if not name:
            self.error_text = "Give the wallet a nickname you'll recognize."
            yield WalletState.auto_dismiss_message
            return
        if len(name) > 40:
            self.error_text = "Keep the nickname under 40 characters."
            yield WalletState.auto_dismiss_message
            return
        if wallet_type not in WALLET_TYPES:
            wallet_type = "Other"
        try:
            balance = float(raw_balance.replace(",", "").replace("₱", "") or 0)
        except ValueError:
            self.error_text = "Balance needs to be a plain number, e.g. 1500."
            yield WalletState.auto_dismiss_message
            return
        if balance < 0:
            self.error_text = "Balance can't be negative — use a Debt wallet."
            yield WalletState.auto_dismiss_message
            return

        user_id = await self._user_id()
        if not user_id:
            self.error_text = "Sign in first to manage wallets."
            yield WalletState.auto_dismiss_message
            return

        editing = self.editing_id
        self.error_text = ""
        self.info_text = ""
        try:
            if editing > 0:
                await asyncio.to_thread(
                    wallet_backend.update_wallet,
                    user_id,
                    editing,
                    name,
                    wallet_type,
                    balance,
                    note,
                )
                self.info_text = f"Updated “{name}”."
            else:
                await asyncio.to_thread(
                    wallet_backend.create_wallet,
                    user_id,
                    name,
                    wallet_type,
                    balance,
                    note,
                )
                self.info_text = f"Wallet “{name}” created."
            self.form_open = False
            self.editing_id = 0
            yield WalletState.refresh
        except ValueError as e:
            self.error_text = str(e)
        except Exception as e:
            logging.exception(f"wallet save failed: {e}")
            self.error_text = "Couldn't save that wallet. Please try again."

        if self.error_text or self.info_text:
            self.message_token += 1
            yield WalletState.auto_dismiss_message

    @rx.event
    async def archive_wallet(self, wallet_id: int):
        yield WalletState.set_archived_flag(int(wallet_id), True)

    @rx.event
    async def restore_wallet(self, wallet_id: int):
        yield WalletState.set_archived_flag(int(wallet_id), False)

    @rx.event
    async def set_archived_flag(self, wallet_id: int, archived: bool):
        self.message_token += 1
        user_id = await self._user_id()
        if not user_id:
            self.error_text = "Sign in first to manage wallets."
            self.message_token += 1
            yield WalletState.auto_dismiss_message
            return
        try:
            await asyncio.to_thread(
                wallet_backend.set_archived,
                user_id,
                wallet_id,
                archived,
            )
            self.info_text = (
                "Wallet archived." if archived else "Wallet restored."
            )
            yield WalletState.refresh
        except Exception as e:
            logging.exception(f"wallet archive toggle failed: {e}")
            self.error_text = "Couldn't update that wallet. Please try again."

        if self.error_text or self.info_text:
            self.message_token += 1
            yield WalletState.auto_dismiss_message


def _to_row(raw: dict) -> WalletRow:
    return WalletRow(
        id=int(raw["id"]),
        name=str(raw["name"]),
        wallet_type=str(raw["wallet_type"]),
        balance=float(raw["balance"]),
        balance_display=wallet_backend.money(float(raw["balance"])),
        note=str(raw.get("note") or ""),
        is_archived=bool(raw["is_archived"]),
        accent=wallet_backend.TYPE_ACCENT.get(raw["wallet_type"], "muted"),
    )
