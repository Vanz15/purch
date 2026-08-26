"""Local (LLM-free) detection of borrowed / lent chat messages.

These messages must NEVER reach the generic purchase extractor — "i
borrowed 250 from Aivann" is a debt, not spending. This module gives the
chat state a cheap, deterministic first pass that recognizes the intent,
the amount, and the person/place involved. When the person can't be
found locally, `purch.wallet_llm.extract_debt_details` is used as a
fallback.

Nothing here touches account numbers or any sensitive account detail — a
wallet is only a nickname, a type, a balance, and a note.
"""

from __future__ import annotations

import re

# Wallet type + display label for each direction.
BORROWED_TYPE = "Debt"
LENT_TYPE = "Lent"
DEFAULT_BORROWED_NAME = "Borrowed"
DEFAULT_LENT_NAME = "Lent"

_LEND_RE = re.compile(
    r"\b(lent|lend|lends|lending|pinautang|nagpautang|pautang|"
    r"pinahiram|nagpahiram)\b",
    re.IGNORECASE,
)
_LEND_PHRASES = ("loaned to", "loan to", "i loaned", "money out to")

_BORROW_RE = re.compile(
    r"\b(borrow|borrowed|borrows|borrowing|utang|umutang|nangutang|"
    r"nautang|owe|owed|owes|hiram|humiram|nanghiram|nghiram)\b",
    re.IGNORECASE,
)
_BORROW_PHRASES = ("loaned from", "loan from", "in debt to", "debt to")

_AMOUNT_RE = re.compile(r"(\d[\d,]*(?:\.\d{1,2})?)")
_NUMERIC_TOKEN_RE = re.compile(r"^[₱$]?\d[\d,]*(?:\.\d{1,2})?$")
_NAME_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z'\u2019.\-]*$")

_PREP_RE = re.compile(
    r"\b(?:to|from|kay|kina|para\s+kay|ni|sa|with|of)\s+(?P<rest>[^,.;!?]+)",
    re.IGNORECASE,
)

_STOP_TOKENS = {
    "a",
    "an",
    "and",
    "at",
    "back",
    "because",
    "cash",
    "for",
    "her",
    "him",
    "his",
    "i",
    "in",
    "it",
    "last",
    "me",
    "mine",
    "money",
    "month",
    "my",
    "of",
    "on",
    "pera",
    "peso",
    "pesos",
    "php",
    "some",
    "someone",
    "that",
    "the",
    "their",
    "them",
    "this",
    "today",
    "tomorrow",
    "total",
    "us",
    "utang",
    "pautang",
    "week",
    "worth",
    "yesterday",
    "you",
    "your",
}

_QUESTION_STARTS = (
    "how",
    "what",
    "when",
    "who",
    "show",
    "list",
    "do i",
    "did i",
    "is there",
    "are there",
)


def _first_hit(
    low: str, pattern: re.Pattern[str], phrases: tuple[str, ...]
) -> int:
    """Index of the earliest keyword hit, or -1 when there is none."""
    positions: list[int] = []
    match = pattern.search(low)
    if match:
        positions.append(match.start())
    for phrase in phrases:
        idx = low.find(phrase)
        if idx >= 0:
            positions.append(idx)
    return min(positions) if positions else -1


def _looks_like_question(message: str) -> bool:
    low = message.strip().lower()
    if low.endswith("?"):
        return True
    return any(low.startswith(start) for start in _QUESTION_STARTS)


def extract_amount(message: str) -> float:
    """First positive number in the message, or 0.0."""
    for raw in _AMOUNT_RE.findall(message or ""):
        try:
            value = float(raw.replace(",", ""))
        except ValueError:
            continue
        if value > 0:
            return round(value, 2)
    return 0.0


def _titleize(token: str) -> str:
    return token if token[:1].isupper() else token.capitalize()


def extract_person(message: str) -> str:
    """Best-effort person/place name after a preposition.

    Handles "borrowed 250 from Aivann", "i lent 300 to Maria Santos",
    "utang kay Aivann 250", and "borrowed 250 to Aivann's store".
    """
    for match in _PREP_RE.finditer(message or ""):
        rest = match.group("rest").strip()
        picked: list[str] = []
        for raw in rest.split():
            token = raw.strip("\"'()[]{}:;\u2018\u2019\u201c\u201d")
            if not token:
                continue
            if _NUMERIC_TOKEN_RE.match(token):
                if picked:
                    break
                continue
            low = token.lower()
            if low in _STOP_TOKENS:
                if picked:
                    break
                continue
            if not _NAME_TOKEN_RE.match(token):
                if picked:
                    break
                continue
            picked.append(token)
            if len(picked) >= 3:
                break
        if picked:
            return " ".join(_titleize(t) for t in picked)[:40]
    return ""


def parse_debt_message(message: str) -> dict[str, str | float] | None:
    """Classify a borrowed/lent message.

    Returns `None` when the message is not about borrowing or lending
    (so the normal agent path runs unchanged). Otherwise returns
    `{"direction", "amount", "person"}` where `amount` may be 0.0 if the
    user didn't say how much.
    """
    text = (message or "").strip()
    if not text:
        return None
    low = text.lower()

    lend_at = _first_hit(low, _LEND_RE, _LEND_PHRASES)
    borrow_at = _first_hit(low, _BORROW_RE, _BORROW_PHRASES)
    if lend_at < 0 and borrow_at < 0:
        return None

    amount = extract_amount(text)
    # "how much do I owe?" is a question, not a new debt entry — let the
    # regular query path answer it.
    if amount <= 0 and _looks_like_question(text):
        return None

    # When both wordings appear, the one the user said first wins.
    if borrow_at < 0:
        direction = "lent"
    elif lend_at < 0:
        direction = "borrowed"
    else:
        direction = "lent" if lend_at < borrow_at else "borrowed"

    return {
        "direction": direction,
        "amount": amount,
        "person": extract_person(text),
    }


def wallet_type_for(direction: str) -> str:
    return LENT_TYPE if direction == "lent" else BORROWED_TYPE


def default_name_for(direction: str) -> str:
    return DEFAULT_LENT_NAME if direction == "lent" else DEFAULT_BORROWED_NAME


def label_for(direction: str) -> str:
    return "Lent" if direction == "lent" else "Borrowed"


def ledger_description(direction: str, person: str) -> str:
    who = person or "someone"
    if direction == "lent":
        return f"Lent money to {who}"
    return f"Borrowed money from {who}"
