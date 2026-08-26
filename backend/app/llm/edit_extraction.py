import json
from llm.groq_client import get_client, THINKING_MODEL
from llm.extraction import CATEGORIES

EDIT_TOOL = {
    "type": "function",
    "function": {
        "name": "extract_edit",
        "description": "Extract what the user wants to change or delete about a past transaction.",
        "parameters": {
            "type": "object",
            "properties": {
                "item_hint": {
                    "type": "string",
                    "description": "Keyword identifying which transaction, if mentioned. Empty string if not specified — assume most recent.",
                },
                "action": {
                    "type": "string",
                    "enum": ["update", "delete"],
                    "description": "'delete' if the user wants to remove the transaction entirely (e.g. 'delete that', 'remove the coffee purchase', or setting the amount to 0). 'update' otherwise.",
                },
                "new_amount": {"type": "number", "description": "New amount, if updating. 0 if not applicable or if deleting."},
                "new_category": {"type": "string", "enum": CATEGORIES + ["none"], "description": "New category, if updating. 'none' if not applicable."},
            },
            "required": ["item_hint", "action", "new_amount", "new_category"],
        },
    },
}

SYSTEM_PROMPT = """Extract what the user wants to change or delete about a logged purchase.
Examples: "actually that was 30 not 3" -> action=update, new_amount=30.
"change yesterday's coffee to 150" -> action=update, item_hint="coffee", new_amount=150.
"delete that" / "remove the coffee purchase" / "cancel that" -> action=delete.
If the user tries to set the amount to 0 (e.g. "make that 0", "change it to 0"), treat this as action=delete too — a zero-value purchase should be removed, not logged as zero."""


def extract_edit(message: str):
    client = get_client()
    response = client.chat.completions.create(
        model=THINKING_MODEL,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": message}],
        tools=[EDIT_TOOL],
        tool_choice={"type": "function", "function": {"name": "extract_edit"}},
        #reasoning_effort="low",
    )
    tool_calls = response.choices[0].message.tool_calls
    if not tool_calls:
        return None
    args = json.loads(tool_calls[0].function.arguments)
    return {
        "action": args.get("action", "update"),
        "item_hint": args.get("item_hint") or None,
        "new_amount": args["new_amount"] if args["new_amount"] > 0 else None,
        "new_category": args["new_category"] if args["new_category"] != "none" else None,
    }