import json
from datetime import date, timedelta
from llm.groq_client import get_client, THINKING_MODEL
from llm.extraction import CATEGORIES

QUERY_TOOL = {
    "type": "function",
    "function": {
        "name": "extract_query_filters",
        "description": "Extract filters from a natural language spending question.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": CATEGORIES + ["all", "unclear"],
                    "description": (
                        "Category to filter by. 'all' if no category mentioned. "
                        "'unclear' if the user used a category-like word that doesn't "
                        "match a real category (e.g. 'unspecified', 'misc') — do not guess."
                    ),
                },
                "category_mode": {
                    "type": "string",
                    "enum": ["include", "exclude"],
                    "description": (
                        "'include' for normal filtering (e.g. 'food transactions'). "
                        "'exclude' when the user says 'non-food', 'not food', "
                        "'excluding food', etc. — meaning everything EXCEPT that category."
                    ),
                },
                "period": {
                    "type": "string",
                    "enum": ["today", "this_week", "this_month", "all_time"],
                    "description": "Time range implied by the question. Default to 'all_time' if unclear.",
                },
                "query_type": {
                    "type": "string",
                    "enum": ["total_spent", "budget_remaining", "list_transactions"],
                    "description": "...",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of most recent transactions to return, if specified. 0 if not specified.",
                },
                "item_hint": {
                    "type": "string",
                    "description": "Specific item keyword if the user asks about one thing, e.g. 'breakfast', 'coffee'. Empty string if they're asking about a category or everything in general.",
                },
            },
            "required": ["category", "category_mode", "period", "query_type", "limit", "item_hint"],
        },
    },
}

SYSTEM_PROMPT = """You extract filters from a spending question so it can be
queried against a database. Always call extract_query_filters.
If no category is mentioned, use "all". If no time period is mentioned, use "all_time".
If the user asks about a SPECIFIC item (e.g. "breakfast", "coffee", "that keyboard"),
set item_hint to that word — this takes priority over category guessing.
If they ask about a category in general (e.g. "food spending"), leave item_hint empty."""


def extract_query_filters(message: str) -> dict:
    """Returns {category, start_date, end_date} ready to use in a DB query."""
    client = get_client()
    response = client.chat.completions.create(
        model=THINKING_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
        tools=[QUERY_TOOL],
        tool_choice={"type": "function", "function": {"name": "extract_query_filters"}},
        #reasoning_effort="low",
    )
    args = json.loads(response.choices[0].message.tool_calls[0].function.arguments)

    category = args.get("category", "all")
    category_mode = args.get("category_mode", "include")
    period = args.get("period", "all_time")

    today = date.today()
    if period == "today":
        start_date = today.isoformat()
    elif period == "this_week":
        start_date = (today - timedelta(days=today.weekday())).isoformat()
    elif period == "this_month":
        start_date = today.replace(day=1).isoformat()
    else:
        start_date = None

    return {
        "category": None if category in ("all", "unclear") else category,
        "category_mode": category_mode,
        "is_unclear": category == "unclear",
        "start_date": start_date,
        "end_date": today.isoformat() if start_date else None,
        "query_type": args.get("query_type", "total_spent"),
        "limit": args.get("limit") or None,
        "item_hint": args.get("item_hint") or None,
    }