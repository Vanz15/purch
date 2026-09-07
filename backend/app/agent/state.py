from typing import TypedDict, Optional


class AgentState(TypedDict):
    """State for handling ONE decomposed action (one raw_segment from the
    original message). run_agent() creates one of these per action and
    dispatches it to the matching handler; see agent/graph.py.
    """
    user_id: str
    message: str                      # the raw_segment for this action
    action_type: Optional[str]        # set by run_agent from decompose_message
    is_purchase: Optional[bool]
    intent: Optional[str]             # only set when is_purchase is False
    item: Optional[str]
    amount: Optional[float]
    category: Optional[str]           # resolved category (post category_resolution)
    transaction_type: Optional[str]   # purchase / given / received / lent / borrowed
    currency: Optional[str]
    transaction_id: Optional[int]
    response: Optional[str]
    pending_edit: Optional[dict]
    pending_conversion: Optional[dict]
    tx_date: Optional[str]
    budget_action: Optional[str]      # set / zero / delete — for budget actions
