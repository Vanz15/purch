import json
from llm.groq_client import get_client, THINKING_MODEL
from llm.extraction import CATEGORIES

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

SYSTEM_PROMPT = f"""Extract a budget category and monthly limit amount.
Valid categories: {', '.join(CATEGORIES)}."""


def extract_budget(message: str):
    client = get_client()
    response = client.chat.completions.create(
        model=THINKING_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
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