import json
import logging

from llm.groq_client import get_client, THINKING_MODEL

logger = logging.getLogger("purch.decompose")

ACTION_TYPES = [
    "log_transaction",   # purchase, given, received, lent, borrowed
    "query_transactions",
    "set_budget",
    "zero_budget",
    "delete_budget",
    "edit_transaction",
    "chat",              # greeting / small talk / no financial action
]

DECOMPOSE_TOOL = {
    "type": "function",
    "function": {
        "name": "decompose_message",
        "description": (
            "Break a user's message into an ORDERED list of one or more "
            "independent financial actions. Most messages contain exactly "
            "one action. Only split into multiple when the message clearly "
            "describes multiple distinct things to do, e.g. separated by "
            "'and', 'also', 'then', commas, or multiple sentences."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "actions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "action_type": {
                                "type": "string",
                                "enum": ACTION_TYPES,
                            },
                            "raw_segment": {
                                "type": "string",
                                "description": (
                                    "The exact portion of the original message this "
                                    "action came from. Copy verbatim — do not "
                                    "paraphrase or summarize. A downstream extractor "
                                    "re-parses this text, so it must keep every "
                                    "number, name, and word the user actually used."
                                ),
                            },
                        },
                        "required": ["action_type", "raw_segment"],
                    },
                },
            },
            "required": ["actions"],
        },
    },
}

SYSTEM_PROMPT = """You split a chat message sent to a personal budget tracker
into an ordered list of one or more independent financial actions.

ACTION TYPES:
- log_transaction: ANY movement of money involving the user — not just
  shopping. This includes:
    * buying something ("fries 100 php", "bought a phone case for 350")
    * giving money away ("gave my mother allowance worth 200 pesos",
      "sent my brother 500", "tipped the driver 50")
    * receiving money ("got 1000 allowance from mom", "refunded 200 for
      the shoes", "received my salary of 15000")
    * lending or borrowing ("lent Jane 300", "borrowed 200 from dad")
  If money changed hands in ANY direction, this is log_transaction —
  even if nothing was "bought."

- query_transactions: asking about past spending, budgets remaining, or
  transaction history ("how much did I spend on food", "food budget left",
  "show my last 5 transactions").

- set_budget: setting or changing a spending limit to a specific positive
  number ("set food budget to 3000", "budget for family is 2000").

- zero_budget: explicitly setting a budget limit to ZERO while keeping the
  budget entry around. Trigger words: "remove", "clear", "reset", "zero
  out" — WITHOUT the word "delete". Example: "remove my budget for
  Family" -> zero_budget.

- delete_budget: permanently deleting the budget entry itself. Trigger
  word: "delete" specifically. Example: "delete my budget for Family" ->
  delete_budget. If wording is genuinely ambiguous between zero_budget and
  delete_budget, prefer zero_budget — it is the less destructive,
  reversible action.

- edit_transaction: correcting or removing a PAST logged transaction
  ("actually that was 30 not 3", "delete that coffee purchase").

- chat: greetings, small talk, or anything with no financial action.

RULES:
1. Most messages are ONE action. Only produce multiple actions when the
   message clearly names multiple distinct things to do — connected by
   "and", "also", "then", commas, or separate sentences.
2. Each action's raw_segment must be copied VERBATIM from the original
   message (not reworded) — it gets re-parsed by a specialized extractor
   downstream, so it must contain all the original wording and numbers.
3. Preserve the ORDER the user mentioned things in.
4. Do not invent actions that aren't in the message.
5. A single message describing one transaction and one instruction
   ("log coffee 100 then delete my family budget") is TWO actions, split
   at the natural boundary — do not merge them into one raw_segment.
6. If you are unsure whether something is a financial action at all,
   prefer log_transaction over chat when a number and something concrete
   is mentioned — the log_transaction extractor has its own fallback if
   it turns out not to be a real transaction.

EXAMPLES:

"gave my mother allowance worth 200 pesos"
-> [{"action_type": "log_transaction", "raw_segment": "gave my mother allowance worth 200 pesos"}]

"fries 100 php and coffee 150"
-> [{"action_type": "log_transaction", "raw_segment": "fries 100 php"},
    {"action_type": "log_transaction", "raw_segment": "coffee 150"}]

"log coffee 150, then delete my Family budget, then set Food budget to 3000"
-> [{"action_type": "log_transaction", "raw_segment": "log coffee 150"},
    {"action_type": "delete_budget", "raw_segment": "delete my Family budget"},
    {"action_type": "set_budget", "raw_segment": "set Food budget to 3000"}]

"remove my budget for Family"
-> [{"action_type": "zero_budget", "raw_segment": "remove my budget for Family"}]

"delete my budget for Family"
-> [{"action_type": "delete_budget", "raw_segment": "delete my budget for Family"}]

"how much did I spend on food this week"
-> [{"action_type": "query_transactions", "raw_segment": "how much did I spend on food this week"}]

"hey how's it going"
-> [{"action_type": "chat", "raw_segment": "hey how's it going"}]

Always call decompose_message.
"""


def decompose_message(message: str) -> list[dict]:
    """Splits a raw message into an ordered list of {action_type, raw_segment}
    dicts. Falls back to a single 'chat' action on any classification
    failure so the caller always has at least one action to dispatch."""
    client = get_client()
    try:
        response = client.chat.completions.create(
            model=THINKING_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
            tools=[DECOMPOSE_TOOL],
            tool_choice={"type": "function", "function": {"name": "decompose_message"}},
        )
        tool_calls = response.choices[0].message.tool_calls
        if not tool_calls:
            return [{"action_type": "chat", "raw_segment": message}]

        args = json.loads(tool_calls[0].function.arguments)
        actions = args.get("actions") or []

        # Defensive filtering — drop malformed entries instead of crashing
        # the whole turn over one bad item.
        clean = []
        for a in actions:
            action_type = a.get("action_type")
            raw_segment = (a.get("raw_segment") or "").strip()
            if action_type in ACTION_TYPES and raw_segment:
                clean.append({"action_type": action_type, "raw_segment": raw_segment})

        if not clean:
            return [{"action_type": "chat", "raw_segment": message}]
        return clean
    except Exception as e:
        logger.exception(f"decompose_message failed, falling back to chat: {e}")
        return [{"action_type": "chat", "raw_segment": message}]
