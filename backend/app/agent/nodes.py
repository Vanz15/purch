from agent.state import AgentState
from llm.extraction import extract_transaction
from llm.tone import generate_comment, generate_fallback_reply, apply_budget_status_tone
from db.models import insert_transaction, get_user_tone
from llm.safety import looks_like_injection
from app.services.category_resolution import resolve_category


def log_transaction_node(state: AgentState) -> AgentState:
    """Handles the log_transaction action: extraction, category resolution,
    currency-conversion gate, insert, and the tone-flavored confirmation
    message. Replaces the old try_extract_node + finalize_add_transaction_node
    pair — those were written only for 'purchases'; this handles any
    transaction_type (purchase/given/received/lent/borrowed)."""
    if looks_like_injection(state["message"]):
        state["is_purchase"] = False
        state["response"] = "I can only help with logging transactions, budgets, and spending questions."
        return state

    extracted = extract_transaction(state["message"])

    if extracted is None:
        state["is_purchase"] = False
        state["response"] = (
            "I didn't catch a transaction in that — try something like "
            "'fries 100 php' or 'gave my mother allowance worth 200 pesos' "
            "and I'll log it for you."
        )
        return state

    if extracted["currency"] != "PHP":
        state["is_purchase"] = True
        state["pending_conversion"] = {
            "item": extracted["item"],
            "category": resolve_category(state["user_id"], extracted["category_hint"]),
            "original_amount": extracted["amount"],
            "original_currency": extracted["currency"],
        }
        state["response"] = (
            f"Got it — {extracted['item']} for {extracted['amount']:.2f} {extracted['currency']}. "
            f"What's that in PHP? Just reply with the peso amount."
        )
        return state

    state["is_purchase"] = True
    state["item"] = extracted["item"]
    state["amount"] = extracted["amount"]
    state["category"] = resolve_category(state["user_id"], extracted["category_hint"])
    state["transaction_type"] = extracted["transaction_type"]
    state["currency"] = extracted["currency"]
    state["tx_date"] = extracted.get("tx_date")

    return _finalize_transaction(state)


def _finalize_transaction(state: AgentState) -> AgentState:
    """Inserts the transaction and builds the tone-flavored confirmation +
    budget warning. Split out from log_transaction_node so
    await_conversion_node can call it after a currency reply too."""
    from db.models import get_budget, get_month_spent

    tx_id = insert_transaction(
        user_id=state["user_id"],
        raw_text=state["message"],
        item=state["item"],
        amount=state["amount"],
        category=state["category"],
        tx_date=state.get("tx_date"),
    )
    state["transaction_id"] = tx_id

    # Detect wallet from the raw segment and apply balance deduction
    try:
        from app.services import wallet_backend
        if wallet_backend.available():
            wallets = wallet_backend.list_wallets(state["user_id"])
            match = wallet_backend.detect_wallet_in_text(wallets, state["message"])
            if match is None:
                try:
                    from app.services import wallet_llm
                    hint = wallet_llm.extract_wallet_reference(state["message"])
                    if hint:
                        match = wallet_backend.match_wallet(wallets, hint)
                except Exception:
                    pass
            if match is not None:
                updated = wallet_backend.apply_purchase(
                    state["user_id"], int(match["id"]),
                    float(state["amount"]), state["item"], tx_id,
                )
                if tx_id:
                    from app.services.db_backend import get_engine
                    from sqlalchemy import text as sa_text
                    try:
                        engine = get_engine()
                        with engine.begin() as conn:
                            conn.execute(
                                sa_text("UPDATE transactions SET wallet = :w WHERE id = :id AND user_id = :uid"),
                                {"w": match["name"], "id": tx_id, "uid": state["user_id"]},
                            )
                    except Exception:
                        pass
                state["wallet_name"] = match.get("name", "")
    except Exception:
        pass

    symbol = "₱" if state["currency"] == "PHP" else "$"
    tone = get_user_tone(state["user_id"])

    try:
        comment = generate_comment(
            state["item"], state["amount"], state["category"], state["currency"], tone
        )
    except Exception:
        comment = ""

    from datetime import date
    date_note = ""
    if state.get("tx_date") and state["tx_date"] != date.today().isoformat():
        date_note = f" (logged for {state['tx_date']})"

    verb = {
        "purchase": "Logged",
        "given": "Logged (given)",
        "received": "Logged (received)",
        "lent": "Logged (lent)",
        "borrowed": "Logged (borrowed)",
    }.get(state.get("transaction_type") or "purchase", "Logged")

    base = f"{verb}: {state['item']} — {symbol}{state['amount']:.2f} ({state['category']}){date_note}"
    if state["category"] == "Other":
        base += " — wasn't sure exactly where this fits, tell me the real category if I got it wrong."
    response = f"{base}\n\n{comment}" if comment else base

    # Budget check — only meaningful for outflows (purchase/given/lent).
    # Received/borrowed money doesn't count against a spending budget.
    if state.get("transaction_type") in (None, "purchase", "given", "lent"):
        limit = get_budget(state["user_id"], state["category"])
        if limit:
            spent = get_month_spent(state["user_id"], state["category"])
            pct = spent / limit
            if pct >= 1.0:
                response += f"\n\n⚠️ You're over your {state['category']} budget: ₱{spent:.2f} / ₱{limit:.2f}"
            elif pct >= 0.8:
                response += f"\n\n⚠️ Heads up — {pct*100:.0f}% of your {state['category']} budget used (₱{spent:.2f} / ₱{limit:.2f})"

    state["response"] = response
    state["raw_segment"] = state.get("message", "")

    # Append wallet note if wallet was auto-linked during _finalize_transaction
    if state.get("wallet_name"):
        try:
            from app.services import wallet_backend
            wallets = wallet_backend.list_wallets(state["user_id"]) if wallet_backend.available() else []
            matched = wallet_backend.match_wallet(wallets, state["wallet_name"]) if wallets else None
            if matched:
                state["wallet_note"] = f"💰 Taken from {matched['name']} — ₱{wallet_backend.money(matched['balance'])} left."
        except Exception:
            pass

    return state


def query_transactions_node(state: AgentState) -> AgentState:
    from llm.query_extraction import extract_query_filters
    from db.models import query_transactions, get_budget, get_month_spent

    filters = extract_query_filters(state["message"])

    if filters["is_unclear"]:
        state["response"] = (
            "I'm not sure what category you mean — try one of your existing "
            "categories, or ask about a specific item."
        )
        return state

    label = filters["item_hint"] or filters["category"] or "all categories"
    category_label = f"non-{label}" if filters["category_mode"] == "exclude" and filters["category"] else label

    if filters["query_type"] == "budget_remaining":
        if not filters["category"] or filters["category_mode"] == "exclude":
            state["response"] = "Budget tracking only works per specific category — try 'how much food budget is left'."
            return state
        limit_amt = get_budget(state["user_id"], filters["category"])
        if limit_amt is None:
            state["response"] = f"You haven't set a budget for {filters['category']} yet."
            return state

        spent = get_month_spent(state["user_id"], filters["category"])
        # A real ₱0 budget (via zero_budget) means "everything spent is
        # over budget" — avoid a ZeroDivisionError and just report that
        # plainly instead of computing a percentage against zero.
        if limit_amt == 0:
            if spent > 0:
                state["response"] = (
                    f"Your {filters['category']} budget is set to ₱0 — "
                    f"₱{spent:.2f} spent this month is all over budget."
                )
            else:
                state["response"] = f"Your {filters['category']} budget is ₱0 and nothing's been spent yet."
            return state
        remaining = limit_amt - spent
        pct = spent / limit_amt

        factual = (
            f"You're ₱{abs(remaining):.2f} over your {filters['category']} budget this month."
            if remaining < 0 else
            f"₱{remaining:.2f} left in your {filters['category']} budget this month (₱{spent:.2f} of ₱{limit_amt:.2f} used)."
        )

        tone = get_user_tone(state["user_id"])
        state["response"] = apply_budget_status_tone(factual, tone, pct)
        return state

    if filters["query_type"] == "list_transactions":
        result = query_transactions(
            user_id=state["user_id"], category=filters["category"], category_mode=filters["category_mode"],
            start_date=filters["start_date"], end_date=filters["end_date"], limit=filters["limit"],
            item_hint=filters["item_hint"],
        )
        if result["count"] == 0:
            state["response"] = "No transactions found for that."
            return state
        lines = [f"- {t['item']}: ₱{t['amount']:.2f} ({t['category']}, {t['tx_timestamp'][:16]})" for t in result["transactions"]]
        state["response"] = f"Your {category_label} transactions:\n" + "\n".join(lines)
        return state

    result = query_transactions(
        user_id=state["user_id"], category=filters["category"], category_mode=filters["category_mode"],
        start_date=filters["start_date"], end_date=filters["end_date"], item_hint=filters["item_hint"],
    )
    if result["count"] == 0:
        state["response"] = "No transactions found for that."
        return state
    state["response"] = (
        f"You spent ₱{result['total']:.2f} across {result['count']} transaction(s) in {category_label}."
    )
    return state


def fallback_reply_node(state: AgentState) -> AgentState:
    """Handles greetings/chat — anything with no financial action."""
    tone = get_user_tone(state["user_id"])
    try:
        state["response"] = generate_fallback_reply(state["message"], tone)
    except Exception:
        state["response"] = (
            "I didn't catch a transaction in that — try something like "
            "'fries 100 php' and I'll log it for you."
        )
    return state


def budget_action_node(state: AgentState) -> AgentState:
    """Handles set_budget / zero_budget / delete_budget actions. All three
    route here — extract_budget_action determines which one actually
    happens, since the user's wording (not the decomposer's label alone)
    is the most reliable signal for set vs. zero vs. delete."""
    from llm.budget_extraction import extract_budget_action
    from db.models import set_budget, zero_budget, delete_budget

    parsed = extract_budget_action(state["message"])
    if parsed is None:
        state["response"] = (
            "I couldn't figure out the budget action — try 'set food budget "
            "to 3000', 'remove my food budget', or 'delete my food budget'."
        )
        return state

    category = resolve_category(state["user_id"], parsed["category_hint"])
    action = parsed["action"]

    if action == "delete":
        deleted = delete_budget(state["user_id"], category)
        state["response"] = (
            f"Deleted your {category} budget."
            if deleted else
            f"You didn't have a budget set for {category}."
        )
    elif action == "zero":
        zero_budget(state["user_id"], category)
        state["response"] = f"{category} budget cleared — set to ₱0."
    else:  # set
        set_budget(state["user_id"], category, parsed["limit_amount"])
        state["response"] = f"Budget set: {category} — ₱{parsed['limit_amount']:.2f}/month"

    state["budget_action"] = action
    state["category"] = category
    return state


def edit_transaction_node(state: AgentState) -> AgentState:
    from llm.edit_extraction import extract_edit
    from db.models import find_best_match_transaction

    parsed = extract_edit(state["message"])
    if parsed is None:
        state["response"] = "What should I change it to? e.g. 'change coffee to ₱150' or 'delete that'."
        return state

    if parsed["action"] == "update" and parsed["new_amount"] is None and parsed["new_category"] is None:
        state["response"] = "What should I change it to? e.g. 'change coffee to ₱150' or 'delete that'."
        return state

    candidates = find_best_match_transaction(state["user_id"], parsed["item_hint"], limit=1)
    if not candidates:
        state["response"] = "I couldn't find a matching transaction."
        return state

    match = candidates[0]

    if parsed["action"] == "delete":
        state["pending_edit"] = {"action": "delete", "transaction_id": match["id"]}
        state["response"] = (
            f"Delete this one — {match['item']} (₱{match['amount']:.2f}, {match['category']}) "
            f"on {match['tx_timestamp'][:16]}? Reply 'yes' to confirm."
        )
        return state

    state["pending_edit"] = {
        "action": "update",
        "transaction_id": match["id"],
        "new_amount": parsed["new_amount"],
        "new_category": parsed["new_category"],
    }
    changes = []
    if parsed["new_amount"]:
        changes.append(f"amount to ₱{parsed['new_amount']:.2f}")
    if parsed["new_category"]:
        changes.append(f"category to {parsed['new_category']}")
    state["response"] = (
        f"Did you mean this one — {match['item']} (₱{match['amount']:.2f}, {match['category']}) "
        f"on {match['tx_timestamp'][:16]}? I'll change {' and '.join(changes)}. Reply 'yes' to confirm."
    )
    return state


def confirm_edit_node(state: AgentState) -> AgentState:
    from db.models import update_transaction
    edit = state.get("pending_edit")
    if not edit:
        state["response"] = "There's no pending edit to confirm."
        return state
    update_transaction(edit["transaction_id"], amount=edit["new_amount"], category=edit["new_category"])
    state["response"] = "Updated!"
    state["pending_edit"] = None
    return state


def await_conversion_node(state: AgentState) -> AgentState:
    return state  # response already set in log_transaction_node
