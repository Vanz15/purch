import json
from llm.groq_client import get_client, THINKING_MODEL

# Fixed fallback category list — used only when a free-text category_hint
# can't be matched against the user's real categories (see
# app.services.category_resolution.resolve_category). This list no longer
# constrains what the model can say; it's the last-resort bucket.
CATEGORIES = [
    "Food", "Transport", "Bills", "Shopping",
    "Entertainment", "Health", "Personal Care", "Family", "Other",
]

# What kind of money movement this is — not just "did they buy something."
# purchase/given are both outflows; received is an inflow; lent/borrowed
# carry an expectation of repayment and are handled like Debt/Lent wallets.
TRANSACTION_TYPES = ["purchase", "given", "received", "lent", "borrowed"]

EXTRACT_TOOL = {
    "type": "function",
    "function": {
        "name": "extract_transaction",
        "description": "Extract a financial transaction's details from a user's message.",
        "parameters": {
            "type": "object",
            "properties": {
                "transaction_type": {
                    "type": "string",
                    "enum": TRANSACTION_TYPES,
                    "description": (
                        "'purchase' = bought something for yourself. "
                        "'given' = gave/sent money to someone else (allowance, "
                        "gift, tip) — still an outflow, just not shopping. "
                        "'received' = money came TO the user (allowance FROM "
                        "someone, refund, salary) — an inflow. "
                        "'lent' = user gave money expecting it back. "
                        "'borrowed' = user received money they owe back."
                    ),
                },
                "item": {
                    "type": "string",
                    "description": (
                        "Short description of what this transaction was, e.g. "
                        "'fries', 'allowance for mother', 'salary'."
                    ),
                },
                "amount": {
                    "type": "number",
                    "description": "The numeric amount involved, no currency symbol",
                },
                "category_hint": {
                    "type": "string",
                    "description": (
                        "Best-fit category NAME as free text, e.g. 'Family', "
                        "'Food', 'Transport', 'Gifts'. Say what it plainly "
                        "sounds like — do NOT force it into a fixed list. The "
                        "caller matches this against the user's real budget "
                        "categories and only falls back to a generic bucket "
                        "if nothing matches."
                    ),
                },
                "date_reference": {
                    "type": "string",
                    "description": "If the user mentions when this happened (e.g. 'yesterday', 'last Monday', 'July 20'), extract it as-is. Empty string if not mentioned — assume today.",
                },
            },
            "required": ["transaction_type", "item", "amount", "category_hint", "date_reference"],
        },
    },
}

SYSTEM_PROMPT = """You extract financial transaction details from short user
messages sent to a personal budget tracker.

A transaction is ANY movement of money involving the user — not only
shopping. This includes buying something, giving money away (allowance,
gifts, tips, sending money to family), receiving money (allowance from
someone, refunds, salary), and lending/borrowing. See transaction_type
for the exact categories and examples.

CATEGORY: category_hint is free text, not a fixed list. Say what the
transaction plainly sounds like it belongs to — "Family" for money given
to a relative, "Food" for food, "Transport" for a ride or fare, and so
on. If truly nothing fits, use "Other". Do not overthink this field —
a downstream step reconciles it against the user's real categories.

CURRENCY: Assume all amounts are in Philippine Pesos (PHP) unless the
user explicitly states another currency (e.g. "$5 USD", "10 dollars",
"10 USD"). Any mention of "USD", "dollars", or "$X USD" means
currency="USD" — this overrides the PHP default. Only use PHP when no
currency is stated or when pesos/PHP is explicitly mentioned.

IMPORTANT: Only call the extract_transaction tool if the message clearly
describes a NEW, real movement of money with a specific subject (e.g.
"fries 100 php", "bought a phone case for 350", "gave my mother allowance
worth 200 pesos", "got 500 from dad"). Do NOT call the tool for:
- Greetings, questions, or general chat
- Corrections to a previous entry, like "actually that was 100",
  "it was 50 not 5", "change that to 200" — these reference an existing
  transaction vaguely ("that", "it") with no real subject, and must be
  treated as NOT a transaction, even though they contain a number.
If the message has a number but nothing concrete happened with money
right now, do NOT call the tool.

Also check whether the user mentions when this happened (e.g.
"yesterday", "last Friday", "July 20") and capture that in date_reference.
If no date is mentioned, leave date_reference empty — it will default to
today.
"""


def extract_transaction(message: str) -> dict | None:
    """Calls Groq with tool-calling to extract transaction details from a raw
    message segment. Returns None if the segment doesn't appear to describe
    an actual movement of money."""
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
        return None  # segment wasn't a transaction — caller decides how to respond

    args = json.loads(tool_calls[0].function.arguments)
    item = args["item"].strip().lower()
    amount = float(args["amount"])

    # Defensive check: reject vague/placeholder items that indicate the
    # model misfired on a correction message rather than a real transaction.
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

    transaction_type = args.get("transaction_type")
    if transaction_type not in TRANSACTION_TYPES:
        transaction_type = "purchase"

    return {
            "item": args["item"],
            "amount": amount,
            "category_hint": (args.get("category_hint") or "Other").strip(),
            "transaction_type": transaction_type,
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