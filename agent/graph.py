from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.nodes import set_budget_node, edit_transaction_node, await_conversion_node
from agent.nodes import (
    try_extract_node,
    finalize_add_transaction_node,
    classify_intent_node,
    query_transactions_node,
    fallback_reply_node,
)

_graph = None


def _purchase_decision(state: AgentState) -> str:
    if state.get("pending_conversion"):
        return "await_conversion"
    return "finalize" if state["is_purchase"] else "classify"


def _intent_decision(state: AgentState) -> str:
    if state["intent"] == "query_transactions":
        return "query"
    elif state["intent"] == "set_budget":
        return "budget"
    elif state["intent"] == "edit_transaction":
        return "edit"
    return "fallback"


def get_graph():
    global _graph
    if _graph is None:
        builder = StateGraph(AgentState)
        builder.add_node("try_extract", try_extract_node)
        builder.add_node("finalize_add_transaction", finalize_add_transaction_node)
        builder.add_node("classify_intent", classify_intent_node)
        builder.add_node("query_transactions", query_transactions_node)
        builder.add_node("set_budget", set_budget_node)
        builder.add_node("fallback_reply", fallback_reply_node)
        builder.add_node("edit_transaction", edit_transaction_node)
        builder.add_node("await_conversion", await_conversion_node)

        builder.set_entry_point("try_extract")
        builder.add_conditional_edges(
            "try_extract", _purchase_decision,
            {"finalize": "finalize_add_transaction", "classify": "classify_intent", "await_conversion": "await_conversion"},
        )
        builder.add_conditional_edges("classify_intent", _intent_decision,
            {"query": "query_transactions", "budget": "set_budget", "edit": "edit_transaction", "fallback": "fallback_reply"}
        )
        builder.add_edge("finalize_add_transaction", END)
        builder.add_edge("query_transactions", END)
        builder.add_edge("set_budget", END)
        builder.add_edge("fallback_reply", END)
        builder.add_edge("edit_transaction", END)
        builder.add_edge("await_conversion", END)

        _graph = builder.compile()
    return _graph


def run_agent(user_id: str, message: str) -> AgentState:
    graph = get_graph()
    initial_state: AgentState = {
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
        "tx_date": None
    }
    result = graph.invoke(initial_state)

    from db.models import log_interaction
    log_interaction(
        user_id=user_id,
        raw_message=message,
        intent=result.get("intent") or ("add_transaction" if result.get("is_purchase") else "unknown"),
        extracted={"item": result.get("item"), "amount": result.get("amount"), "category": result.get("category")} if result.get("item") else None,
        response=result.get("response"),
    )
    return result