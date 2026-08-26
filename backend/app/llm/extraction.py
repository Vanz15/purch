import json
from llm.groq_client import get_client, THINKING_MODEL

# Fixed category list — keeps categorization consistent instead of letting
# the model invent new categories freely (see earlier discussion on category drift).
CATEGORIES = [
    "Food", "Transport", "Bills", "Shopping",
    "Entertainment", "Health", "Personal Care", "Other",
]

EXTRACT_TOOL = {
    "type": "function",
    "function": {
        "name": "extract_transaction",
        "description": "Extract a purchase's item, amount, and category from a user's message.",
        "parameters": {
            "type": "object",
            "properties": {
                "item": {
                    "type": "string",
                    "description": "Short description of what was purchased, e.g. 'fries'",
                },
                "amount": {
                    "type": "number",
                    "description": "The numeric cost of the purchase, no currency symbol",
                },
                "category": {
                    "type": "string",
                    "enum": CATEGORIES,
                    "description": "Best-fit category for this purchase",
                },
                "date_reference": {
                    "type": "string",
                    "description": "If the user mentions when this happened (e.g. 'yesterday', 'last Monday', 'July 20'), extract it as-is. Empty string if not mentioned — assume today.",
                },
            },
            "required": ["item", "amount", "category", "date_reference"],
        },
    },
}

SYSTEM_PROMPT = f"""You extract purchase details from short user messages.
Valid categories are: {', '.join(CATEGORIES)}.
If the category isn't obvious, use "Other".

Assume all amounts are in Philippine Pesos (PHP) unless the user explicitly
states another currency (e.g. "$5 USD", "10 dollars", "10 USD"). Any mention
of "USD", "dollars", or "$X USD" means currency="USD" — this overrides the
PHP default. Only use PHP when no currency is stated or when pesos/PHP is
explicitly mentioned.

IMPORTANT: Only call the extract_transaction tool if the message clearly
describes a NEW purchase with a specific, real item (e.g. "fries 100 php",
"bought a phone case for 350"). Do NOT call the tool for:
- Greetings, questions, or general chat
- Corrections to a previous entry, like "actually that was 100",
  "it was 50 not 5", "change that to 200" — these reference an existing
  transaction vaguely ("that", "it") with no real item name, and must be
  treated as NOT a purchase, even though they contain a number.
If the message has a number but no concrete item being purchased right now,
do NOT call the tool.

Also check whether the user mentions when the purchase happened (e.g.
"yesterday", "last Friday", "July 20") and capture that in date_reference.
If no date is mentioned, leave date_reference empty — it will default to today.
"""


def extract_transaction(message: str) -> dict | None:
    """Calls Groq with tool-calling to extract {item, amount, category} from a raw message.
    Returns None if the message doesn't appear to describe a purchase."""
    client = get_client()

    response = client.chat.completions.create(
        model=THINKING_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
        tools=[EXTRACT_TOOL],
        tool_choice="auto",
        #reasoning_effort="low",
    )

    choice = response.choices[0]
    tool_calls = choice.message.tool_calls

    if not tool_calls:
        return None  # message wasn't a purchase — caller decides how to respond

    args = json.loads(tool_calls[0].function.arguments)
    item = args["item"].strip().lower()
    amount = float(args["amount"])

    # Defensive check: reject vague/placeholder items that indicate the
    # model misfired on a correction message rather than a real purchase.
    vague_items = {"unknown", "it", "that", "this", "n/a", "none", ""}
    if item in vague_items:
        return None

    if amount <= 0:
        return None

    currency = args.get("currency", "PHP")
    message_lower = message.lower()
    if any(kw in message_lower for kw in ["usd", "us$", "dollar", "dollars"]):
        currency = "USD"
    elif any(kw in message_lower for kw in ["php", "peso", "pesos"]):
        currency = "PHP"
    category = args.get("category")
    if category not in CATEGORIES:
        category = "Other"

    return {
            "item": args["item"],
            "amount": amount,
            "category": category,
            "currency": currency,
            "tx_date": resolve_date_reference(args.get("date_reference")),
    }

def resolve_date_reference(date_ref: str) -> str:
    """Converts a natural date reference into an ISO date string (YYYY-MM-DD).
    Returns None if empty or unparseable — caller should default to today."""
    if not date_ref:
        return None
    from datetime import date, timedelta
    today = date.today()
    lower = date_ref.lower().strip()
    if lower in ("today", ""):
        return today.isoformat()
    if lower == "yesterday":
        return (today - timedelta(days=1)).isoformat()
    try:
        from dateutil import parser
        parsed = parser.parse(date_ref, fuzzy=True, default=today)
        resolved = parsed.date()
        if resolved > today:
            return today.isoformat()  # never log a purchase in the future
        return resolved.isoformat()
    except Exception:
        return None