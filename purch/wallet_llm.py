"""Groq-backed wallet reference + wallet question extraction.

Reuses the same tool-calling pattern (and the already-hardened
`llm.groq_client.get_client` wrapper installed by
`purch.groq_helper.install_safe_groq_calls`) as the rest of the LLM
layer, so retries, model fallbacks, and secret-safe logging all apply
here too.

Nothing in this module ever asks for account numbers or any sensitive
account detail — only a wallet nickname/type hint.
"""

from __future__ import annotations

import json
import logging

from llm.groq_client import THINKING_MODEL, get_client

from purch.wallet_backend import WALLET_TYPES

_WALLET_REF_TOOL = {
    "type": "function",
    "function": {
        "name": "extract_wallet_reference",
        "description": (
            "Extract which wallet / money source a purchase was paid from, "
            "if the user mentioned one."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "wallet_hint": {
                    "type": "string",
                    "description": (
                        "The wallet nickname or money-source word the user "
                        "used, e.g. 'cash', 'gcash', 'bdo savings', "
                        "'baon wallet'. Empty string if they did not say "
                        "where the money came from."
                    ),
                },
            },
            "required": ["wallet_hint"],
        },
    },
}

_WALLET_QUERY_TOOL = {
    "type": "function",
    "function": {
        "name": "extract_wallet_query",
        "description": (
            "Decide whether the user is asking about their wallet balances "
            "or spending allowance, and which wallet they mean."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "is_wallet_question": {
                    "type": "boolean",
                    "description": (
                        "True only if the user is asking how much money is "
                        "in a wallet / how much they can still spend from a "
                        "money source. False for purchases, budgets, or chat."
                    ),
                },
                "wallet_hint": {
                    "type": "string",
                    "description": (
                        "Wallet nickname or type word they asked about. "
                        "Empty string if they asked about everything."
                    ),
                },
                "query_type": {
                    "type": "string",
                    "enum": ["balance", "allowance", "list"],
                    "description": (
                        "'balance' for a single wallet amount, 'allowance' "
                        "for how much is still spendable, 'list' for an "
                        "overview of all wallets."
                    ),
                },
            },
            "required": ["is_wallet_question", "wallet_hint", "query_type"],
        },
    },
}

_DEBT_TOOL = {
    "type": "function",
    "function": {
        "name": "extract_debt_details",
        "description": (
            "Extract whether the user borrowed money from someone or lent "
            "money to someone, how much, and who/where is involved."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "is_debt_message": {
                    "type": "boolean",
                    "description": (
                        "True only when the user is recording money they "
                        "borrowed (they now owe it) or money they lent out "
                        "(they expect it back). False for normal purchases, "
                        "budgets, or questions."
                    ),
                },
                "direction": {
                    "type": "string",
                    "enum": ["borrowed", "lent", "none"],
                    "description": (
                        "'borrowed' when the user received money they owe, "
                        "'lent' when the user gave money they expect back."
                    ),
                },
                "amount": {
                    "type": "number",
                    "description": "Amount involved. 0 if not stated.",
                },
                "person": {
                    "type": "string",
                    "description": (
                        "Name of the person or place involved, e.g. 'Aivann', "
                        "'Mama', 'Aling Nena's store'. Empty string if the "
                        "user did not name anyone. Never invent a name."
                    ),
                },
            },
            "required": [
                "is_debt_message",
                "direction",
                "amount",
                "person",
            ],
        },
    },
}

_DEBT_PROMPT = (
    "You read a short money message from a budget tracker and extract "
    "whether it records borrowed money (the user now owes it) or lent "
    "money (the user expects it back), the amount, and the person or place "
    "involved. Treat 'borrowed 250 to Aivann' and 'borrowed 250 from "
    "Aivann' both as borrowed from Aivann. Never invent a name, never ask "
    "for or extract account numbers or card details. Always call the tool."
)

_REF_PROMPT = (
    "You read a short expense message and extract only which money source "
    "or wallet it was paid from, if stated. Wallet types users may refer to: "
    f"{', '.join(WALLET_TYPES)}. Never invent a wallet — if the user did not "
    "say where the money came from, return an empty wallet_hint. Never ask "
    "for or extract account numbers or card details."
)

_QUERY_PROMPT = (
    "You classify whether a budget-tracker message is a question about the "
    "user's wallets (how much money is in cash / bank / savings, how much "
    "they can still spend from a wallet). Always call the tool. Category "
    "budget questions are NOT wallet questions."
)


def extract_wallet_reference(message: str) -> str:
    """Return a wallet hint string ("" when none was mentioned)."""
    try:
        client = get_client()
        response = client.chat.completions.create(
            model=THINKING_MODEL,
            messages=[
                {"role": "system", "content": _REF_PROMPT},
                {"role": "user", "content": message},
            ],
            tools=[_WALLET_REF_TOOL],
            tool_choice={
                "type": "function",
                "function": {"name": "extract_wallet_reference"},
            },
        )
        tool_calls = response.choices[0].message.tool_calls
        if not tool_calls:
            return ""
        args = json.loads(tool_calls[0].function.arguments)
        hint = str(args.get("wallet_hint") or "").strip()
        return "" if hint.lower() in ("none", "n/a", "unknown") else hint
    except Exception as e:
        logging.exception(f"wallet reference extraction failed: {e}")
        return ""


def extract_debt_details(message: str) -> dict[str, str | bool | float]:
    """LLM fallback for borrowed/lent messages the local parser only
    partially understood (usually a missing person or amount)."""
    fallback: dict[str, str | bool | float] = {
        "is_debt_message": False,
        "direction": "none",
        "amount": 0.0,
        "person": "",
    }
    try:
        client = get_client()
        response = client.chat.completions.create(
            model=THINKING_MODEL,
            messages=[
                {"role": "system", "content": _DEBT_PROMPT},
                {"role": "user", "content": message},
            ],
            tools=[_DEBT_TOOL],
            tool_choice={
                "type": "function",
                "function": {"name": "extract_debt_details"},
            },
        )
        tool_calls = response.choices[0].message.tool_calls
        if not tool_calls:
            return fallback
        args = json.loads(tool_calls[0].function.arguments)
        person = str(args.get("person") or "").strip()
        if person.lower() in ("none", "n/a", "unknown", "someone"):
            person = ""
        try:
            amount = float(args.get("amount") or 0)
        except (TypeError, ValueError):
            amount = 0.0
        return {
            "is_debt_message": bool(args.get("is_debt_message")),
            "direction": str(args.get("direction") or "none"),
            "amount": round(max(amount, 0.0), 2),
            "person": person[:40],
        }
    except Exception as e:
        logging.exception(f"debt detail extraction failed: {e}")
        return fallback


def extract_wallet_query(message: str) -> dict[str, str | bool]:
    """Classify a wallet allowance/balance question."""
    fallback: dict[str, str | bool] = {
        "is_wallet_question": False,
        "wallet_hint": "",
        "query_type": "list",
    }
    try:
        client = get_client()
        response = client.chat.completions.create(
            model=THINKING_MODEL,
            messages=[
                {"role": "system", "content": _QUERY_PROMPT},
                {"role": "user", "content": message},
            ],
            tools=[_WALLET_QUERY_TOOL],
            tool_choice={
                "type": "function",
                "function": {"name": "extract_wallet_query"},
            },
        )
        tool_calls = response.choices[0].message.tool_calls
        if not tool_calls:
            return fallback
        args = json.loads(tool_calls[0].function.arguments)
        return {
            "is_wallet_question": bool(args.get("is_wallet_question")),
            "wallet_hint": str(args.get("wallet_hint") or "").strip(),
            "query_type": str(args.get("query_type") or "list"),
        }
    except Exception as e:
        logging.exception(f"wallet query extraction failed: {e}")
        return fallback
