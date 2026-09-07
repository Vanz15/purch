import json
from llm.groq_client import get_client, THINKING_MODEL
from llm.extraction import CATEGORIES

BUDGET_ACTIONS = ["set", "zero", "delete"]

BUDGET_ACTION_TOOL = {
    "type": "function",
    "function": {
        "name": "extract_budget_action",
        "description": "Extract a budget action: set a new limit, zero it out, or delete it.",
        "parameters": {
            "type": "object",
            "properties": {
                "category_hint": {
                    "type": "string",
                    "description": (
                        "Category name as free text, e.g. 'Family', 'Food'. "
                        "Do not force it into a fixed list — say what it "
                        "plainly sounds like."
                    ),
                },
                "action": {
                    "type": "string",
                    "enum": BUDGET_ACTIONS,
                    "description": (
                        "'set' — the user gave a specific positive limit "
                        "amount to set or change the budget to. "
                        "'zero' — the user wants the budget cleared/reset "
                        "to zero but the entry can stay (words like "
                        "'remove', 'clear', 'reset' WITHOUT 'delete'). "
                        "'delete' — the user wants the budget entry itself "
                        "gone (the word 'delete' specifically)."
                    ),
                },
                "limit_amount": {
                    "type": "number",
                    "description": "New limit amount if action='set'. 0 if action is 'zero' or 'delete'.",
                },
            },
            "required": ["category_hint", "action", "limit_amount"],
        },
    },
}

SYSTEM_PROMPT = """Extract a budget action from a user's message: setting a
new limit, zeroing a budget out, or deleting it entirely.

- "set food budget to 3000" / "budget for family is 2000"
  -> action=set, category_hint="Food"/"Family", limit_amount=3000/2000
- "remove my budget for Family" / "clear my food budget" / "reset transport
  budget" -> action=zero, category_hint accordingly, limit_amount=0
- "delete my budget for Family" / "delete the food budget"
  -> action=delete, category_hint="Family"/"Food", limit_amount=0

The word "delete" specifically means action=delete. Words like "remove",
"clear", or "reset" WITHOUT the word "delete" mean action=zero — the
less destructive, reversible choice. If genuinely ambiguous, prefer zero
over delete.

category_hint is free text — say what the category plainly sounds like
(e.g. "Family", "Food", "Transport"). Do not force it into a fixed list.
"""


def extract_budget_action(message: str) -> dict | None:
    """Returns {category_hint, action, limit_amount} or None on failure.
    limit_amount is only meaningful when action == 'set'."""
    client = get_client()
    try:
        response = client.chat.completions.create(
            model=THINKING_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
            tools=[BUDGET_ACTION_TOOL],
            tool_choice={"type": "function", "function": {"name": "extract_budget_action"}},
        )
        tool_calls = response.choices[0].message.tool_calls
        if not tool_calls:
            return None
        args = json.loads(tool_calls[0].function.arguments)
        action = args.get("action")
        if action not in BUDGET_ACTIONS:
            return None
        category_hint = (args.get("category_hint") or "").strip()
        if not category_hint:
            return None
        limit_amount = float(args.get("limit_amount") or 0)
        if action == "set" and limit_amount <= 0:
            return None  # a 'set' with no real amount isn't actionable
        return {"category_hint": category_hint, "action": action, "limit_amount": limit_amount}
    except Exception:
        return None


# --- Legacy function, kept for backward compatibility -----------------
# Older call sites may still import extract_budget directly. New code
# should use extract_budget_action, which also supports zero/delete.
BUDGET_TOOL = {
    "type": "function",
    "function": {
        "name": "extract_budget",
        "description": "Extract a budget category and limit amount from a message.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "enum": CATEGORIES},
                "limit_amount": {"type": "number"},
            },
            "required": ["category", "limit_amount"],
        },
    },
}

LEGACY_SYSTEM_PROMPT = f"""Extract a budget category and monthly limit amount.
Valid categories: {', '.join(CATEGORIES)}."""


def extract_budget(message: str):
    client = get_client()
    response = client.chat.completions.create(
        model=THINKING_MODEL,
        messages=[
            {"role": "system", "content": LEGACY_SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
        tools=[BUDGET_TOOL],
        tool_choice={"type": "function", "function": {"name": "extract_budget"}},
        #reasoning_effort="low",
    )
    tool_calls = response.choices[0].message.tool_calls
    if not tool_calls:
        return None
    args = json.loads(tool_calls[0].function.arguments)
    if args["limit_amount"] <= 0:
        return None
    return {"category": args["category"], "limit_amount": float(args["limit_amount"])}