from typing import TypedDict, Optional


class AgentState(TypedDict):
    user_id: str
    message: str
    is_purchase: Optional[bool]      # NEW — set by try_extract_node
    intent: Optional[str]            # only set when is_purchase is False
    item: Optional[str]
    amount: Optional[float]
    category: Optional[str]
    currency: Optional[str]          # NEW — carried forward so we don't re-extract
    transaction_id: Optional[int]
    response: Optional[str]
    pending_edit: Optional[dict] 
    pending_conversion: Optional[dict]
    tx_date: Optional[str]