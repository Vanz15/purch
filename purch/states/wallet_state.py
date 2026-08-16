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
    pct: int
    group: str


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

    # Two-step delete: first click parks the wallet id here so only that
    # card reveals its Cancel / Confirm delete controls. Nothing is
    # removed until `confirm_delete` runs.
    pending_delete_id: int = 0
    pending_delete_name: str = ""
    is_deleting: bool = False

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

    # Grouped wallet analytics: Debit (Bank/Cash/Savings), Lent, and
    # Borrowed (Debt/Loan). Split into separate lists so the UI renders
    # each group with its own heading + insight without nested foreach.
    debit_bars: list[WalletRow] = []
    lent_bars: list[WalletRow] = []
    borrowed_bars: list[WalletRow] = []
    debit_total_display: str = "0.00"
    lent_total_display: str = "0.00"
    borrowed_total_display: str = "0.00"
    debit_insight: str = ""
    lent_insight: str = ""
    borrowed_insight: str = ""

    @rx.var
    def has_wallets(self) -> bool:
        return len(self.wallets) > 0

    @rx.var
    def has_liabilities(self) -> bool:
        return len(self.borrowed_bars) > 0

    @rx.var
    def has_debit_wallets(self) -> bool:
        return len(self.debit_bars) > 0

    @rx.var
    def has_lent_wallets(self) -> bool:
        return len(self.lent_bars) > 0

    @rx.var
    def has_borrowed_wallets(self) -> bool:
        return len(self.borrowed_bars) > 0

    @rx.var
    def has_pending_delete(self) -> bool:
        return self.pending_delete_id > 0

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
                self._reset_analytics()
                return

            self.unavailable = False
            user_id = await self._user_id()
            if not user_id:
                self.unauthenticated = True
                self.wallets = []
                self.archived_wallets = []
                self.has_loaded = True
                self._reset_analytics()
                return

            self.unauthenticated = False
            rows = await asyncio.to_thread(
                wallet_backend.list_wallets, user_id, True
            )
            active_raw = [r for r in rows if not r["is_archived"]]
            archived_raw = [r for r in rows if r["is_archived"]]
            peak = max(
                (abs(float(r["balance"])) for r in active_raw), default=0.0
            )
            active = [_to_row(r, peak) for r in active_raw]
            archived = [_to_row(r, 0.0) for r in archived_raw]
            self.wallets = active
            self.archived_wallets = archived

            totals = wallet_backend.summary(active_raw)
            self.assets_display = wallet_backend.money(totals["assets"])
            self.liabilities_display = wallet_backend.money(
                totals["liabilities"]
            )
            self.net_display = wallet_backend.money(totals["net"])
            self._build_groups(active)
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
    # Wallet analytics helpers
    # ------------------------------------------------------------------ #

    def _remove_wallet_locally(self, wallet_id: int) -> None:
        """Drop a deleted wallet from the in-memory lists and rebuild the
        summary tiles + grouped analytics from the rows that remain.

        Runs in the same event as the delete so the card disappears
        immediately, without waiting for the follow-up refresh round trip.
        """
        wid = int(wallet_id)
        remaining_active = [w for w in self.wallets if int(w["id"]) != wid]
        remaining_archived = [
            WalletRow(**dict(w))
            for w in self.archived_wallets
            if int(w["id"]) != wid
        ]

        # Share bars are relative to the largest remaining balance, so the
        # percentages have to be rescaled once a wallet is gone.
        peak = max(
            (abs(float(w["balance"])) for w in remaining_active), default=0.0
        )
        rescaled: list[WalletRow] = []
        for w in remaining_active:
            row = dict(w)
            balance = abs(float(row["balance"]))
            row["pct"] = (
                int(min(round((balance / peak) * 100), 100)) if peak else 0
            )
            rescaled.append(WalletRow(**row))

        self.wallets = rescaled
        self.archived_wallets = remaining_archived

        totals = wallet_backend.summary(
            [
                {
                    "balance": float(w["balance"]),
                    "wallet_type": str(w["wallet_type"]),
                }
                for w in rescaled
            ]
        )
        self.assets_display = wallet_backend.money(totals["assets"])
        self.liabilities_display = wallet_backend.money(totals["liabilities"])
        self.net_display = wallet_backend.money(totals["net"])
        self._build_groups(rescaled)

    def _move_wallet_locally(self, wallet_id: int, archived: bool) -> None:
        """Move a wallet between the active and archived lists in place.

        Runs in the same event as the archive/restore write so the card
        visibly moves immediately, without depending on a follow-up
        refresh round trip firing.
        """
        wid = int(wallet_id)
        target: WalletRow | None = None
        for row in list(self.wallets) + list(self.archived_wallets):
            if int(row["id"]) == wid:
                target = WalletRow(**dict(row))
                break
        if target is None:
            return

        target["is_archived"] = bool(archived)
        active = [w for w in self.wallets if int(w["id"]) != wid]
        archived_rows = [
            WalletRow(**dict(w))
            for w in self.archived_wallets
            if int(w["id"]) != wid
        ]

        if archived:
            target["pct"] = 0
            archived_rows.append(target)
        else:
            active.append(target)

        # Share bars are relative to the largest remaining active balance,
        # so the percentages have to be rescaled whenever the set changes.
        peak = max((abs(float(w["balance"])) for w in active), default=0.0)
        rescaled: list[WalletRow] = []
        for w in sorted(active, key=lambda r: str(r["name"]).lower()):
            row = dict(w)
            balance = abs(float(row["balance"]))
            row["pct"] = (
                int(min(round((balance / peak) * 100), 100)) if peak else 0
            )
            rescaled.append(WalletRow(**row))

        self.wallets = rescaled
        self.archived_wallets = sorted(
            archived_rows, key=lambda r: str(r["name"]).lower()
        )

        totals = wallet_backend.summary(
            [
                {
                    "balance": float(w["balance"]),
                    "wallet_type": str(w["wallet_type"]),
                }
                for w in rescaled
            ]
        )
        self.assets_display = wallet_backend.money(totals["assets"])
        self.liabilities_display = wallet_backend.money(totals["liabilities"])
        self.net_display = wallet_backend.money(totals["net"])
        self._build_groups(rescaled)

    async def _write_archive_flag(self, wallet_id: int, archived: bool) -> str:
        """Flip a wallet's archive flag for the signed-in user.

        Performs the write directly (no yielded same-state event) so the
        behavior is identical whether it's triggered from the UI or from
        an event test. Returns "" on success, or a user-facing message.
        """
        wid = int(wallet_id)
        if wid <= 0:
            return "That wallet no longer exists."
        user_id = await self._user_id()
        if not user_id:
            return "Sign in first to manage wallets."
        if not wallet_backend.available():
            return "Wallet storage is unavailable right now. Please try again."
        try:
            await asyncio.to_thread(
                wallet_backend.set_archived, user_id, wid, bool(archived)
            )
        except Exception as e:
            logging.exception(f"wallet archive flag write failed: {e}")
            return "Couldn't update that wallet. Please try again."
        return ""

    def _reset_analytics(self) -> None:
        self.assets_display = "0.00"
        self.liabilities_display = "0.00"
        self.net_display = "0.00"
        self._build_groups([])

    def _build_groups(self, rows: list[WalletRow]) -> None:
        """Split active wallets into Debit / Lent / Borrowed and write a
        short, human balance insight for each group."""
        debit = [r for r in rows if r["group"] == "Debit"]
        lent = [r for r in rows if r["group"] == "Lent"]
        borrowed = [r for r in rows if r["group"] == "Borrowed"]

        self.debit_bars = debit
        self.lent_bars = lent
        self.borrowed_bars = borrowed

        debit_total = sum(r["balance"] for r in debit)
        lent_total = sum(r["balance"] for r in lent)
        borrowed_total = sum(r["balance"] for r in borrowed)

        self.debit_total_display = wallet_backend.money(debit_total)
        self.lent_total_display = wallet_backend.money(lent_total)
        self.borrowed_total_display = wallet_backend.money(borrowed_total)

        if not debit:
            self.debit_insight = (
                "No cash, bank, or savings wallets yet — add one to track "
                "what you can spend."
            )
        else:
            top = max(debit, key=lambda r: r["balance"])
            share = (
                int(round((top["balance"] / debit_total) * 100))
                if debit_total
                else 0
            )
            self.debit_insight = (
                f"{len(debit)} wallet(s) holding ₱"
                f"{wallet_backend.money(debit_total)} — "
                f"{top['name']} carries {share}% of it."
            )

        if not lent:
            self.lent_insight = "Nothing lent out right now."
        else:
            self.lent_insight = (
                f"₱{wallet_backend.money(lent_total)} is out with "
                f"{len(lent)} wallet(s) — money you still expect back."
            )

        if not borrowed:
            self.borrowed_insight = "No debts or loans tracked — you're clear."
        else:
            cover = (
                int(round((debit_total / borrowed_total) * 100))
                if borrowed_total
                else 0
            )
            self.borrowed_insight = (
                f"₱{wallet_backend.money(borrowed_total)} owed across "
                f"{len(borrowed)} wallet(s) — your debit wallets cover "
                f"{cover}% of it."
            )

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

    # ------------------------------------------------------------------ #
    # Two-step delete
    # ------------------------------------------------------------------ #

    @rx.event
    def request_delete(self, wallet_id: int):
        """First click — reveal the confirmation UI for this wallet only.
        Deliberately performs no database work."""
        target: WalletRow | None = None
        for row in list(self.wallets) + list(self.archived_wallets):
            if int(row["id"]) == int(wallet_id):
                target = row
                break
        if target is None:
            return
        self.pending_delete_id = int(wallet_id)
        self.pending_delete_name = target["name"]
        self.error_text = ""
        self.info_text = ""

    @rx.event
    def cancel_delete(self):
        self.pending_delete_id = 0
        self.pending_delete_name = ""
        self.is_deleting = False

    @rx.event
    async def confirm_delete(self):
        """Second click — actually remove the wallet and its ledger rows."""
        wallet_id = int(self.pending_delete_id)
        if wallet_id <= 0 or self.is_deleting:
            return
        name = self.pending_delete_name
        self.message_token += 1
        user_id = await self._user_id()
        if not user_id:
            self.error_text = "Sign in first to manage wallets."
            self.pending_delete_id = 0
            self.pending_delete_name = ""
            self.message_token += 1
            yield WalletState.auto_dismiss_message
            return

        self.is_deleting = True
        self.error_text = ""
        self.info_text = ""
        yield

        try:
            deleted = await asyncio.to_thread(
                wallet_backend.delete_wallet, user_id, wallet_id
            )
            if deleted is None:
                self.error_text = "That wallet no longer exists."
            else:
                self.info_text = (
                    f"Deleted \u201c{deleted or name}\u201d and its ledger "
                    "history."
                )
            # The row is gone from the database (or never existed) either
            # way — drop it from state now, in this same event, and rebuild
            # totals/analytics from what's left.
            self._remove_wallet_locally(wallet_id)
            self.pending_delete_id = 0
            self.pending_delete_name = ""
            self.is_deleting = False
            if self.form_open and self.editing_id == wallet_id:
                self.form_open = False
                self.editing_id = 0
            if not self.archived_wallets:
                self.show_archived = False
            yield
            yield WalletState.refresh
        except Exception as e:
            logging.exception(f"wallet delete failed: {e}")
            self.error_text = "Couldn't delete that wallet. Please try again."
        finally:
            self.is_deleting = False

        self.message_token += 1
        yield WalletState.auto_dismiss_message

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
        """Archive a wallet. The write happens in this same event — the
        secondary delete confirmation flow is untouched, and a wallet
        awaiting delete confirmation simply has that confirmation
        dismissed."""
        wid = int(wallet_id)
        self.message_token += 1
        error = await self._write_archive_flag(wid, True)
        if error:
            self.error_text = error
            self.info_text = ""
        else:
            self.error_text = ""
            self.info_text = "Wallet archived."
            self._move_wallet_locally(wid, True)
            if self.pending_delete_id == wid:
                self.pending_delete_id = 0
                self.pending_delete_name = ""
                self.is_deleting = False
            if self.form_open and self.editing_id == wid:
                self.form_open = False
                self.editing_id = 0
        self.message_token += 1
        yield
        if not error:
            yield WalletState.refresh
        yield WalletState.auto_dismiss_message

    @rx.event
    async def restore_wallet(self, wallet_id: int):
        """Restore an archived wallet back into the active grid."""
        wid = int(wallet_id)
        self.message_token += 1
        error = await self._write_archive_flag(wid, False)
        if error:
            self.error_text = error
            self.info_text = ""
        else:
            self.error_text = ""
            self.info_text = "Wallet restored."
            self._move_wallet_locally(wid, False)
            if self.pending_delete_id == wid:
                self.pending_delete_id = 0
                self.pending_delete_name = ""
                self.is_deleting = False
            if not self.archived_wallets:
                self.show_archived = False
        self.message_token += 1
        yield
        if not error:
            yield WalletState.refresh
        yield WalletState.auto_dismiss_message

    @rx.event
    async def set_archived_flag(self, wallet_id: int, archived: bool):
        """Kept for direct callers — performs the same in-event write as
        `archive_wallet` / `restore_wallet` rather than delegating to a
        yielded same-state event."""
        wid = int(wallet_id)
        self.message_token += 1
        error = await self._write_archive_flag(wid, bool(archived))
        if error:
            self.error_text = error
            self.info_text = ""
        else:
            self.error_text = ""
            self.info_text = (
                "Wallet archived." if archived else "Wallet restored."
            )
            self._move_wallet_locally(wid, bool(archived))
            if not self.archived_wallets:
                self.show_archived = False
        self.message_token += 1
        yield
        if not error:
            yield WalletState.refresh
        yield WalletState.auto_dismiss_message


def _to_row(raw: dict, peak: float = 0.0) -> WalletRow:
    balance = float(raw["balance"])
    pct = int(min(round((abs(balance) / peak) * 100), 100)) if peak else 0
    return WalletRow(
        id=int(raw["id"]),
        name=str(raw["name"]),
        wallet_type=str(raw["wallet_type"]),
        balance=round(balance, 2),
        balance_display=wallet_backend.money(balance),
        note=str(raw.get("note") or ""),
        is_archived=bool(raw["is_archived"]),
        accent=wallet_backend.TYPE_ACCENT.get(raw["wallet_type"], "muted"),
        pct=pct,
        group=wallet_backend.group_for(raw["wallet_type"]),
    )
