from llm.groq_client import get_client, THINKING_MODEL

VALID_INTENTS = ["add_transaction", "query_transactions", "set_budget", "edit_transaction"]

INTENT_TOOL = {
    "type": "function",
    "function": {
        "name": "classify_intent",
        "description": "Classify what the user wants to do with their budget tracker.",
        "parameters": {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "enum": VALID_INTENTS,
                    "description": (
                        "'add_transaction' if the message describes a purchase to log "
                        "(e.g. 'fries $2', 'bought a phone case for 350'). "
                        "'query_transactions' if the message asks about past spending "
                        "(e.g. 'how much did I spend this week', 'show my food spending')."
                        "set_budget: the user wants to set or change a spending limit (e.g. 'set my food budget to 3000')."
                        "edit_transaction: user wants to correct/change a past entry (e.g. 'that was actually 30 not 3')."
                    ),
                },
            },
            "required": ["intent"],
        },
    },
}

SYSTEM_PROMPT = """You classify budget tracker chat messages into one of two intents:
- add_transaction: the user is telling you about a purchase to log
- query_transactions: the user is asking about their past spending

Always call the classify_intent tool. If the message is neither (a greeting,
random chat), default to add_transaction — the add_transaction node already
handles non-purchase messages gracefully."""


def classify_intent(message: str) -> str:
    """Returns 'add_transaction' or 'query_transactions'. Defaults to
    'add_transaction' on any classification failure, since that node
    already has a graceful fallback for non-purchase messages."""
    client = get_client()
    try:
        response = client.chat.completions.create(
            model=THINKING_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
            tools=[INTENT_TOOL],
            tool_choice={"type": "function", "function": {"name": "classify_intent"}},
            #reasoning_effort="low",
        )
        tool_calls = response.choices[0].message.tool_calls
        if not tool_calls:
            return "add_transaction"

        import json
        args = json.loads(tool_calls[0].function.arguments)
        intent = args.get("intent", "add_transaction")
        return intent if intent in VALID_INTENTS else "add_transaction"
    except Exception:
        return "add_transaction"