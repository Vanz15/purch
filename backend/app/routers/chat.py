"""Chat API — ports ChatState.send_message (and friends) to HTTP.

Statelessness (Option A from the plan): the client round-trips the
pending conversational state (`pending_edit`, `pending_conversion`,
`pending_wallet`, `wallet_choices`, `awaiting_wallet`) in the request
and receives it back in the response. No server-side session store.

Branch order in `send_message` is load-bearing and MUST stay:
  1. Wallet-selection gate (hard block)
  2. Debt/lent intent
  3. Wallet balance question
  4. Pending currency conversion reply
  5. Pending edit confirmation
  6. Full agent round-trip (fallback)
"""
import asyncio
import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.deps import get_current_user_id
from app.services import bootstrap as backend
from app.services import wallet_backend, wallet_intent
from app.services.errors import safe_banner_message, safe_error_message

logger = logging.getLogger("purch.chat")

router = APIRouter(prefix="/api/chat", tags=["chat"])

PROMPT_CHIPS: list[str] = [
    "milk tea 85 gcash",
    "grab ride 240 cash",
    "borrowed 250 from Aivann",
    "lent 300 to Maria",
    "how much this week?",
    "set food budget to 3000",
]


# --------------------------------------------------------------------------- #
# Request / response models
# --------------------------------------------------------------------------- #
class ChatRequest(BaseModel):
    message: str
    pending_edit: dict | None = None
    pending_conversion: dict | None = None
    pending_wallet: dict | None = None
    wallet_choices: list[dict] | None = None
    awaiting_wallet: bool = False


class WalletChoice(BaseModel):
    id: int
    name: str
    wallet_type: str
    balance_display: str


class ChatResponse(BaseModel):
    response: str
    meta: str = ""
    alert: str = ""  # "" | "warning" | "danger"
    pending_edit: dict | None = None
    pending_conversion: dict | None = None
    pending_wallet: dict | None = None
    wallet_choices: list[WalletChoice] = []
    awaiting_wallet: bool = False


class ChooseWalletRequest(BaseModel):
    wallet_id: int
    pending_wallet: dict | None = None


# --------------------------------------------------------------------------- #
# Helpers (ported from ChatState private methods)
# --------------------------------------------------------------------------- #
def _now_str() -> str:
    from app.services.time_utils import now_display

    return now_display("")


def _wallet_selection_required(req: ChatRequest) -> bool:
    return bool(
        req.pending_wallet
        or req.wallet_choices
        or req.awaiting_wallet
    )


def _wallet_choice_payload(wallets: list[dict]) -> list[WalletChoice]:
    return [
        WalletChoice(
            id=int(w["id"]),
            name=str(w["name"]),
            wallet_type=str(w["wallet_type"]),
            balance_display=wallet_backend.money(w["balance"]),
        )
        for w in wallets
    ]


def _build_prompt_chips(user_id: str) -> list[str]:
    wallets = wallet_backend.list_wallets(user_id) if wallet_backend.available() else []
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


def _wallet_query_reply(user_id: str, prompt: str, ctx) -> str:
    if ctx.pending_conversion or ctx.pending_edit:
        return ""
    low = prompt.lower().strip()
    if not low:
        return ""
    wallets = wallet_backend.list_wallets(user_id) if wallet_backend.available() else []
    if not wallets:
        return ""

    wallet_words = ["wallet", "wallets", "allowance", "balance", "funds"]
    for keywords in wallet_backend.TYPE_KEYWORDS.values():
        wallet_words.extend(keywords)
    wallet_words.extend(w["name"].lower() for w in wallets)
    if not any(word and word in low for word in wallet_words):
        return ""

    question_markers = (
        "how much", "how many", "left", "remaining", "balance", "allowance",
        "show", "list", "what's in", "whats in", "do i have", "available", "?",
    )
    if not any(marker in low for marker in question_markers):
        return ""

    try:
        from app.services import wallet_llm

        parsed = wallet_llm.extract_wallet_query(prompt)
    except Exception as e:
        logger.exception(f"wallet query classification failed: {e}")
        parsed = {"is_wallet_question": True, "wallet_hint": "", "query_type": "list"}

    if not parsed.get("is_wallet_question"):
        return ""

    hint = str(parsed.get("wallet_hint") or "")
    match = wallet_backend.match_wallet(wallets, hint) or wallet_backend.detect_wallet_in_text(
        wallets, prompt
    )
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


def _debt_intent_reply(user_id: str, prompt: str) -> str:
    if not wallet_backend.available():
        return ""
    parsed = wallet_intent.parse_debt_message(prompt)
    if parsed is None:
        return ""

    direction = str(parsed["direction"])
    amount = float(parsed["amount"] or 0)
    person = str(parsed["person"] or "")

    if not person or amount <= 0:
        try:
            from app.services import wallet_llm

            details = wallet_llm.extract_debt_details(prompt)
        except Exception as e:
            logger.exception(f"debt detail fallback failed: {e}")
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
        example = person or ("Aivann" if direction == "borrowed" else "Maria")
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
            user_id, wallet_name, wallet_type, amount, description
        )
    except Exception as e:
        logger.exception(f"debt wallet upsert failed: {e}")
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


def _handle_pending_conversion(prompt: str, user_id: str) -> tuple[str, str, bool] | None:
    conv = backend.__dict__.get("_pending_conversion")
    # We use the request-scoped pending_conversion, passed in via ctx; see route.
    return None  # replaced by route-level logic


def _apply_wallet_for_last_tx(user_id: str, prompt: str, tx: dict) -> str:
    if not tx:
        return ""
    wallets = wallet_backend.list_wallets(user_id) if wallet_backend.available() else []
    if not wallets:
        return ""

    amount = float(tx.get("amount") or 0)
    item = str(tx.get("item") or "purchase")
    tx_id = int(tx.get("transaction_id") or 0)

    match = wallet_backend.detect_wallet_in_text(wallets, prompt)
    if match is None:
        try:
            from app.services import wallet_llm

            hint = wallet_llm.extract_wallet_reference(prompt)
        except Exception as e:
            logger.exception(f"wallet reference lookup failed: {e}")
            hint = ""
        if hint:
            match = wallet_backend.match_wallet(wallets, hint)

    if match is not None:
        updated = wallet_backend.apply_purchase(
            user_id, int(match["id"]), amount, item, tx_id or None
        )
        if updated is not None:
            return (
                f"💰 Taken from {updated['name']} — ₱"
                f"{wallet_backend.money(updated['balance'])} left."
            )

    return ""  # caller parks the tx and returns wallet chips


def _default_cash_for_last_tx(user_id: str, tx: dict) -> str:
    """No wallets exist yet: log the purchase against a Cash wallet by default
    so balances stay meaningful, without forcing the user to pick one."""
    try:
        wallets = wallet_backend.list_wallets(user_id) if wallet_backend.available() else []
        cash = next(
            (w for w in wallets if str(w.get("wallet_type", "")).lower() == "cash"
             or str(w.get("name", "")).lower() == "cash"),
            None,
        )
        if cash is None:
            wid = wallet_backend.create_wallet(user_id, "Cash", "Cash", 0.0, "Default cash wallet")
        else:
            wid = cash["id"]
        updated = wallet_backend.apply_purchase(
            user_id, int(wid), float(tx.get("amount") or 0),
            str(tx.get("item") or "purchase"), int(tx.get("transaction_id") or 0) or None,
        )
        if updated is not None:
            return f"💰 Logged to Cash — ₱{wallet_backend.money(updated['balance'])} balance."
    except Exception as e:
        logger.exception(f"default cash wallet failed: {e}")
    return "Logged as cash (no wallet set up yet — add one anytime to track balances)."


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
class _Ctx:
    """Mutable per-request conversational context (replaces Reflex state)."""

    def __init__(self, req: ChatRequest):
        self.pending_edit = req.pending_edit
        self.pending_conversion = req.pending_conversion
        self.pending_wallet = req.pending_wallet
        self.wallet_choices = req.wallet_choices or []
        self.awaiting_wallet = req.awaiting_wallet


@router.post("", response_model=ChatResponse)
async def send_message(req: ChatRequest, user_id: str = Depends(get_current_user_id)):
    backend.bootstrap()
    backend.ensure_user(user_id)

    # ---- Branch 1: wallet-selection HARD GATE -------------------------------
    if _wallet_selection_required(req):
        choices = req.wallet_choices or []
        if not choices:
            wallets = wallet_backend.list_wallets(user_id) if wallet_backend.available() else []
            choices = [
                c.model_dump() for c in _wallet_choice_payload(wallets)
            ]
        raise HTTPException(
            status_code=409,
            detail="Pick a wallet for your last purchase first — tap one of the wallet buttons above.",
        )

    prompt = (req.message or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Type something first — even 'coffee 150' works.")

    ctx = _Ctx(req)
    response_text = ""
    meta = ""
    fatal_error = False
    last_tx: dict = {}

    try:
        if not (os.getenv("GROQ_API_KEY") or "").strip() and not ctx.pending_conversion and not ctx.pending_edit:
            raise RuntimeError("credentials unavailable")

        # ---- Branch 2: debt/lent intent (before generic extraction) ---------
        debt_answer = _debt_intent_reply(user_id, prompt)

        # ---- Branch 3: wallet balance question ------------------------------
        wallet_answer = (
            ""
            if debt_answer
            else _wallet_query_reply(user_id, prompt, ctx)
        )

        # ---- Branch 4: pending currency conversion --------------------------
        conv_reply = None
        if not (debt_answer or wallet_answer) and ctx.pending_conversion:
            conv = ctx.pending_conversion
            try:
                php_amount = float(str(prompt).strip().replace(",", ""))
            except ValueError:
                php_amount = 0.0
            if php_amount > 0:
                item = str(conv.get("item", ""))
                category = str(conv.get("category", "Other"))
                tx_id = backend.insert_transaction(user_id, prompt, item, php_amount, category)
                last_tx = {
                    "transaction_id": int(tx_id or 0),
                    "amount": php_amount,
                    "item": item,
                }
                tone = backend.get_user_tone(user_id)
                try:
                    comment = backend.generate_comment(item, php_amount, category, "PHP", tone)
                except Exception as e:
                    logger.exception(f"Comment generation failed: {e}")
                    comment = ""
                response_text = f"Logged: {item} — ₱{php_amount:.2f} ({category})"
                if comment:
                    response_text += f"\n\n{comment}"
                meta = f"{category} • ₱{php_amount:.0f} • Today"
                ctx.pending_conversion = None
                conv_reply = (response_text, meta, False)

        if debt_answer:
            response_text = debt_answer
        elif wallet_answer:
            response_text = wallet_answer
        elif conv_reply is not None:
            response_text, meta, fatal_error = conv_reply
        else:
            # ---- Branch 5: pending edit confirmation ------------------------
            edit_reply = None
            edit = ctx.pending_edit
            if edit and prompt.strip().lower() in ("yes", "y", "confirm", "yep", "sure"):
                try:
                    tx_id = int(edit.get("transaction_id", 0))
                    if edit.get("action") == "delete":
                        backend.delete_transaction(tx_id)
                        ctx.pending_edit = None
                        edit_reply = ("Deleted.", "", False)
                    else:
                        backend.update_transaction(
                            tx_id,
                            amount=float(edit["new_amount"]) if edit.get("new_amount") else None,
                            category=str(edit["new_category"]) if edit.get("new_category") else None,
                        )
                        ctx.pending_edit = None
                        edit_reply = ("Updated!", "", False)
                except Exception as e:
                    logger.exception(f"Edit confirm failed: {e}")
                    edit_reply = (safe_error_message(e), "", True)

            if edit_reply is not None:
                response_text, meta, fatal_error = edit_reply
            else:
                # ---- Branch 6: full agent round-trip -----------------------
                result = backend.run_agent(user_id, prompt)
                response_text = result.get("response") or ""
                if result.get("pending_conversion"):
                    pc = result["pending_conversion"]
                    ctx.pending_conversion = {
                        "item": str(pc.get("item", "")),
                        "category": str(pc.get("category", "Other")),
                        "original_amount": float(pc.get("original_amount", 0) or 0),
                        "original_currency": str(pc.get("original_currency", "")),
                    }
                if result.get("pending_edit"):
                    pe = result["pending_edit"]
                    ctx.pending_edit = {
                        "action": str(pe.get("action", "update")),
                        "transaction_id": int(pe.get("transaction_id", 0) or 0),
                        "new_amount": float(pe.get("new_amount") or 0),
                        "new_category": str(pe.get("new_category") or ""),
                    }
                if (
                    result.get("transaction_id")
                    and result.get("category")
                    and result.get("amount") is not None
                ):
                    meta = f"{result['category']} • ₱{float(result['amount']):.0f} • Today"
                    last_tx = {
                        "transaction_id": int(result["transaction_id"] or 0),
                        "amount": float(result["amount"]),
                        "item": str(result.get("item") or "purchase"),
                    }
    except Exception as e:
        logger.exception(f"send_message failed: {e}")
        response_text = safe_error_message(e)
        fatal_error = True

    if not response_text:
        response_text = safe_error_message(RuntimeError("empty response"))
        fatal_error = True

    # ---- Wallet linking: subtract from named wallet or park + offer chips --
    pending_wallet_resp = None
    awaiting_wallet = False
    wallet_choices: list[WalletChoice] = []
    if not fatal_error and last_tx:
        try:
            wallet_note = _apply_wallet_for_last_tx(user_id, prompt, last_tx)
        except Exception as e:
            logger.exception(f"wallet linking failed: {e}")
            wallet_note = ""
        if wallet_note:
            response_text = f"{response_text}\n\n{wallet_note}"
        else:
            wallets = wallet_backend.list_wallets(user_id) if wallet_backend.available() else []
            if not wallets:
                # No wallets yet → default the purchase to a Cash wallet; no gate.
                wallet_note = _default_cash_for_last_tx(user_id, last_tx)
                response_text = f"{response_text}\n\n{wallet_note}"
            else:
                pending_wallet_resp = {
                    "transaction_id": last_tx["transaction_id"],
                    "amount": last_tx["amount"],
                    "item": last_tx["item"],
                }
                wallet_choices = _wallet_choice_payload(wallets)
                awaiting_wallet = True
                response_text = (
                    f"{response_text}\n\n"
                    "Which wallet did this come from? Tap one below to finish "
                    "logging it — a wallet is required."
                )

    alert = backend.classify_alert(response_text)

    return ChatResponse(
        response=response_text,
        meta=meta,
        alert=alert,
        pending_edit=ctx.pending_edit,
        pending_conversion=ctx.pending_conversion,
        pending_wallet=pending_wallet_resp,
        wallet_choices=wallet_choices,
        awaiting_wallet=awaiting_wallet,
    )


@router.post("/choose-wallet", response_model=ChatResponse)
async def choose_wallet(req: ChooseWalletRequest, user_id: str = Depends(get_current_user_id)):
    backend.bootstrap()
    backend.ensure_user(user_id)
    pending = req.pending_wallet
    if not pending:
        return ChatResponse(response="")
    try:
        updated = wallet_backend.apply_purchase(
            user_id,
            int(req.wallet_id),
            float(pending.get("amount") or 0),
            pending.get("item") or "purchase",
            int(pending.get("transaction_id") or 0) or None,
        )
    except Exception as e:
        logger.exception(f"wallet apply failed: {e}")
        updated = None

    if updated is None:
        wallets = wallet_backend.list_wallets(user_id) if wallet_backend.available() else []
        return ChatResponse(
            response="I couldn't update that wallet just now — please pick one again.",
            wallet_choices=_wallet_choice_payload(wallets),
            awaiting_wallet=True,
            pending_wallet=pending,
        )
    return ChatResponse(
        response=(
            f"💰 Logged against {updated['name']} — ₱"
            f"{wallet_backend.money(updated['balance'])} left."
        )
    )


@router.get("/prompt-chips", response_model=list[str])
async def prompt_chips(user_id: str = Depends(get_current_user_id)):
    backend.bootstrap()
    backend.ensure_user(user_id)
    try:
        return _build_prompt_chips(user_id)
    except Exception as e:
        logger.exception(f"prompt chip refresh failed: {e}")
        return list(PROMPT_CHIPS)
