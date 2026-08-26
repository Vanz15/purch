"""Wallets API — ports WalletState to HTTP.

Validation rules preserved exactly from WalletState.submit_wallet:
  * name required, max 40 characters
  * wallet_type not in WALLET_TYPES -> silently coerce to "Other"
  * balance parsed from string (',' and '₱' stripped), must be >= 0
    (negative balances rejected with "Balance can't be negative — use a Debt wallet.")
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.deps import get_current_user_id
from app.services import wallet_backend

logger = logging.getLogger("purch.wallets")

router = APIRouter(prefix="/api/wallets", tags=["wallets"])


class WalletCreate(BaseModel):
    name: str
    wallet_type: str = "Other"
    balance: str = "0"  # kept as string to mirror the old form_data path
    note: str = ""


class WalletUpdate(BaseModel):
    name: str
    wallet_type: str = "Other"
    balance: str = "0"
    note: str = ""


def _parse_balance(raw: str) -> float:
    try:
        return float(str(raw).replace(",", "").replace("₱", "") or 0)
    except ValueError:
        raise HTTPException(status_code=422, detail="Balance needs to be a plain number, e.g. 1500.")


def _build_rows(user_id: str, include_archived: bool):
    """Mirror WalletState.refresh: active/archived split + grouped analytics."""
    rows = wallet_backend.list_wallets(user_id, True) if wallet_backend.available() else []
    active_raw = [r for r in rows if not r["is_archived"]]
    archived_raw = [r for r in rows if r["is_archived"]]
    peak = max((abs(float(r["balance"])) for r in active_raw), default=0.0)

    def _to_row(raw, peak):
        balance = float(raw["balance"])
        pct = int(min(round((abs(balance) / peak) * 100), 100)) if peak else 0
        return {
            "id": int(raw["id"]),
            "name": str(raw["name"]),
            "wallet_type": str(raw["wallet_type"]),
            "balance": round(balance, 2),
            "balance_display": wallet_backend.money(balance),
            "note": str(raw.get("note") or ""),
            "is_archived": bool(raw["is_archived"]),
            "accent": wallet_backend.TYPE_ACCENT.get(raw["wallet_type"], "muted"),
            "pct": pct,
            "group": wallet_backend.group_for(raw["wallet_type"]),
        }

    active = [_to_row(r, peak) for r in active_raw]
    archived = [_to_row(r, 0.0) for r in archived_raw]
    return rows, active, archived, active_raw


def _build_groups(active_raw: list[dict]) -> dict:
    """Mirror WalletState._build_groups: Debit/Lent/Borrowed + insights."""
    rows = []
    peak = max((abs(float(r["balance"])) for r in active_raw), default=0.0)
    for r in active_raw:
        balance = float(r["balance"])
        pct = int(min(round((abs(balance) / peak) * 100), 100)) if peak else 0
        rows.append({
            "balance": balance,
            "wallet_type": str(r["wallet_type"]),
            "name": str(r["name"]),
            "pct": pct,
            "group": wallet_backend.group_for(r["wallet_type"]),
        })

    debit = [r for r in rows if r["group"] == "Debit"]
    lent = [r for r in rows if r["group"] == "Lent"]
    borrowed = [r for r in rows if r["group"] == "Borrowed"]

    debit_total = sum(r["balance"] for r in debit)
    lent_total = sum(r["balance"] for r in lent)
    borrowed_total = sum(r["balance"] for r in borrowed)

    totals = wallet_backend.summary(active_raw)
    out = {
        "debit_bars": debit,
        "lent_bars": lent,
        "borrowed_bars": borrowed,
        "debit_total_display": wallet_backend.money(debit_total),
        "lent_total_display": wallet_backend.money(lent_total),
        "borrowed_total_display": wallet_backend.money(borrowed_total),
        "assets_display": wallet_backend.money(totals["assets"]),
        "liabilities_display": wallet_backend.money(totals["liabilities"]),
        "net_display": wallet_backend.money(totals["net"]),
    }
    out["debit_insight"] = (
        "No cash, bank, or savings wallets yet — add one to track what you can spend."
        if not debit else
        f"{len(debit)} wallet(s) holding ₱{wallet_backend.money(debit_total)} — "
        f"{max(debit, key=lambda r: r['balance'])['name']} carries "
        f"{int(round((max(debit, key=lambda r: r['balance'])['balance'] / debit_total) * 100)) if debit_total else 0}% of it."
    )
    out["lent_insight"] = (
        "Nothing lent out right now."
        if not lent else
        f"₱{wallet_backend.money(lent_total)} is out with {len(lent)} wallet(s) — money you still expect back."
    )
    out["borrowed_insight"] = (
        "No debts or loans tracked — you're clear."
        if not borrowed else
        f"₱{wallet_backend.money(borrowed_total)} owed across {len(borrowed)} wallet(s) — your debit wallets cover "
        f"{int(round((debit_total / borrowed_total) * 100)) if borrowed_total else 0}% of it."
    )
    return out


@router.get("")
async def list_wallets(include_archived: bool = False, user_id: str = Depends(get_current_user_id)):
    if not wallet_backend.available():
        raise HTTPException(status_code=503, detail="Wallet storage is unavailable right now.")
    _, active, archived, _ = _build_rows(user_id, True)
    return {"wallets": active if not include_archived else active + archived}


@router.post("")
async def create_wallet(body: WalletCreate, user_id: str = Depends(get_current_user_id)):
    if not body.name.strip():
        raise HTTPException(status_code=422, detail="Give the wallet a nickname you'll recognize.")
    if len(body.name) > 40:
        raise HTTPException(status_code=422, detail="Keep the nickname under 40 characters.")
    wallet_type = body.wallet_type if body.wallet_type in wallet_backend.WALLET_TYPES else "Other"
    balance = _parse_balance(body.balance)
    if balance < 0:
        raise HTTPException(status_code=422, detail="Balance can't be negative — use a Debt wallet.")
    try:
        wallet_backend.create_wallet(user_id, body.name.strip(), wallet_type, balance, body.note)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"ok": True}


@router.put("/{wallet_id}")
async def update_wallet(wallet_id: int, body: WalletUpdate, user_id: str = Depends(get_current_user_id)):
    if not body.name.strip():
        raise HTTPException(status_code=422, detail="Give the wallet a nickname you'll recognize.")
    if len(body.name) > 40:
        raise HTTPException(status_code=422, detail="Keep the nickname under 40 characters.")
    wallet_type = body.wallet_type if body.wallet_type in wallet_backend.WALLET_TYPES else "Other"
    balance = _parse_balance(body.balance)
    if balance < 0:
        raise HTTPException(status_code=422, detail="Balance can't be negative — use a Debt wallet.")
    try:
        wallet_backend.update_wallet(user_id, wallet_id, body.name.strip(), wallet_type, balance, body.note)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"ok": True}


@router.delete("/{wallet_id}")
async def delete_wallet(wallet_id: int, user_id: str = Depends(get_current_user_id)):
    if not wallet_backend.available():
        raise HTTPException(status_code=503, detail="Wallet storage is unavailable right now.")
    deleted_name = wallet_backend.delete_wallet(user_id, wallet_id)
    if deleted_name is None:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return {"deleted": deleted_name}


@router.post("/{wallet_id}/archive")
async def archive_wallet(wallet_id: int, user_id: str = Depends(get_current_user_id)):
    if not wallet_backend.available():
        raise HTTPException(status_code=503, detail="Wallet storage is unavailable right now.")
    wallet_backend.set_archived(user_id, wallet_id, True)
    return {"ok": True}


@router.post("/{wallet_id}/restore")
async def restore_wallet(wallet_id: int, user_id: str = Depends(get_current_user_id)):
    if not wallet_backend.available():
        raise HTTPException(status_code=503, detail="Wallet storage is unavailable right now.")
    wallet_backend.set_archived(user_id, wallet_id, False)
    return {"ok": True}


@router.get("/summary")
async def wallets_summary(user_id: str = Depends(get_current_user_id)):
    """Grouped analytics + insight strings (moved server-side from the old
    WalletState._build_groups client computation)."""
    if not wallet_backend.available():
        raise HTTPException(status_code=503, detail="Wallet storage is unavailable right now.")
    _, _, _, active_raw = _build_rows(user_id, True)
    return _build_groups(active_raw)
