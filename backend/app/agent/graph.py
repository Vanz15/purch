"""Dispatches a raw chat message to one or more action handlers.

This replaced the old single-path LangGraph StateGraph (one message ->
one classification -> one handler -> END). A message can now describe
several independent things to do ("log coffee 150, then delete my Family
budget, then set Food budget to 3000") — decompose_message() splits it
into an ordered list of {action_type, raw_segment}, and this module runs
each one through its handler in order, in isolation, then combines the
replies into one response.

IMPORTANT for app/routers/chat.py compatibility: chat.py reads specific
keys off the dict this module returns — response, pending_conversion,
pending_edit, transaction_id, category, amount, item. Those keys are
populated from the LAST action that set them (see _merge_into_final
below), so a currency-conversion prompt or an edit-confirmation prompt
raised by any action in the batch still surfaces correctly, and the most
recent logged transaction still gets its meta/receipt treatment in the
UI. If you add a new action type, make sure any state chat.py depends on
is copied over in _merge_into_final too.
"""
from llm.decompose import decompose_message
from agent.state import AgentState
from agent.nodes import (
    log_transaction_node,
    query_transactions_node,
    budget_action_node,
    fallback_reply_node,
    edit_transaction_node,
    await_conversion_node,
)

ACTION_HANDLERS = {
    "log_transaction": log_transaction_node,
    "query_transactions": query_transactions_node,
    "set_budget": budget_action_node,
    "zero_budget": budget_action_node,
    "delete_budget": budget_action_node,
    "edit_transaction": edit_transaction_node,
    "chat": fallback_reply_node,
}


def _new_segment_state(user_id: str, action_type: str, raw_segment: str) -> AgentState:
    return {
        "user_id": user_id,
        "message": raw_segment,
        "action_type": action_type,
        "is_purchase": None,
        "intent": None,
        "item": None,
        "amount": None,
        "category": None,
        "transaction_type": None,
        "currency": None,
        "transaction_id": None,
        "response": None,
        "pending_edit": None,
        "pending_conversion": None,
        "tx_date": None,
        "budget_action": None,
    }


def _merge_into_final(final: dict, result: AgentState) -> None:
    """Carries forward whatever chat.py needs from this action's result.
    Later actions in the same message win, mirroring 'the last relevant
    thing that happened' — e.g. if the user logs two transactions in one
    message, the second one's receipt/meta is what the UI highlights."""
    for key in (
        "pending_conversion", "pending_edit", "transaction_id",
        "category", "amount", "item", "currency", "tx_date",
        "transaction_type", "intent", "is_purchase", "wallet_name",
        "wallet_note",
    ):
        value = result.get(key)
        if value is not None:
            final[key] = value

    # Collect every logged transaction for per-segment wallet linking
    if result.get("transaction_id") and result.get("is_purchase"):
        final.setdefault("transactions", []).append({
            "transaction_id": int(result["transaction_id"]),
            "amount": float(result.get("amount") or 0),
            "item": str(result.get("item") or "purchase"),
            "raw_segment": str(result.get("message") or ""),
            "wallet": str(result.get("wallet_name") or ""),
            "wallet_note": str(result.get("wallet_note") or ""),
        })


def run_agent(user_id: str, message: str) -> dict:
    actions = decompose_message(message)
    responses: list[str] = []

    final: dict = {
        "user_id": user_id,
        "message": message,
        "is_purchase": None,
        "intent": None,
        "item": None,
        "amount": None,
        "category": None,
        "currency": None,
        "transaction_id": None,
        "response": None,
        "pending_edit": None,
        "pending_conversion": None,
        "tx_date": None,
        "transactions": [],
    }

    for action in actions:
        segment_state = _new_segment_state(user_id, action["action_type"], action["raw_segment"])
        handler = ACTION_HANDLERS.get(action["action_type"], fallback_reply_node)
        result = handler(segment_state)

        if result.get("response"):
            responses.append(result["response"])

        _merge_into_final(final, result)

        # A currency-conversion prompt or an edit-confirmation prompt both
        # expect the user's NEXT message to answer them directly (see
        # chat.py branch order). If either fires mid-batch, stop processing
        # further actions in this same message — anything after it would
        # run before the conversation actually resolves the pending state,
        # which would be confusing rather than helpful.
        if result.get("pending_conversion") or result.get("pending_edit"):
            break

    final["response"] = "\n\n".join(responses) if responses else "Got it."

    from db.models import log_interaction
    log_interaction(
        user_id=user_id,
        raw_message=message,
        intent="multi_action" if len(actions) > 1 else actions[0]["action_type"],
        extracted={"actions": actions},
        response=final["response"],
    )
    return final
