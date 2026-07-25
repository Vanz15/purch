"""Purch — chat-based budget tracker."""
import time
import streamlit as st

from db.connection import init_db, ensure_user
from db.models import get_user_tone, set_user_tone, get_budget, get_month_spent
from llm.extraction import CATEGORIES
from agent.graph import run_agent
from ui.styles import inject_custom_css
from ui.gauges import semi_circular_gauge

RECEIPT_ICON = "assets/receipt_icon.png"
st.set_page_config(page_title="Purch", page_icon=RECEIPT_ICON, layout="wide", initial_sidebar_state="expanded")

# --- Auth gate ---
if not st.user.is_logged_in:
    inject_custom_css()
    st.html("""
    <div class="empty-state">
        <h2>Welcome to Purch!</h2>
        <p>Your last purchase eventually leads to another. Log it. Own it.</p>
    </div>
    """)
    _, center, _ = st.columns([1, 1, 1])
    with center:
        if st.button("Log in with Google", use_container_width=True):
            st.login()
    st.stop()

USER_ID = st.user.email
init_db()
ensure_user(USER_ID)

inject_custom_css()

from llm.tone import VALID_TONES
TONE_OPTIONS = VALID_TONES

# --- Session state ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_edit" not in st.session_state:
    st.session_state.pending_edit = None
if "pending_conversion" not in st.session_state:
    st.session_state.pending_conversion = None
if "request_count" not in st.session_state:
    st.session_state.request_count = 0
    st.session_state.request_window_start = time.time()

def stream_text(text: str):
    import time as time_module
    for word in text.split(" "):
        yield word + " "
        time_module.sleep(0.02)


def classify_alert(text: str) -> str:
    lower = text.lower()
    if "over your" in lower and "budget" in lower:
        return "danger"
    if "heads up" in lower or "almost" in lower:
        return "warning"
    return ""


def render_chat_message(msg: dict) -> None:
    if msg["role"] == "user":
        avatar = getattr(st.user, "picture", None) or "🧑"
        with st.chat_message("user", avatar=avatar):
            st.markdown(f'<div class="user-bubble"><p>{msg["content"]}</p></div>', unsafe_allow_html=True)
    else:
        alert = classify_alert(msg["content"])
        alert_class = f" alert-{alert}" if alert else ""
        alert_html = ""
        if alert == "danger":
            alert_html = '<div class="alert-header" style="color:var(--red);"><i class="ti ti-alert-triangle-filled"></i><span>Over Budget</span></div>'
        elif alert == "warning":
            alert_html = '<div class="alert-header" style="color:var(--amber);"><i class="ti ti-alert-triangle-filled"></i><span>Budget Warning</span></div>'

        content_html = msg["content"].replace("\n", "<br>")
        with st.chat_message("assistant", avatar="assets/receipt_icon.png"):
            st.markdown(
                f'<div class="assistant-bubble{alert_class}">{alert_html}<p>{content_html}</p></div>',
                unsafe_allow_html=True,
            )


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
        "<h2 style='margin:0.4rem 0 20px 0;'>Purch <span class='beta-badge'>Beta</span></h2>",
        unsafe_allow_html=True,
        )

        st.markdown("<p class='section-label'>Assistant Tone</p>", unsafe_allow_html=True)
        current_tone = get_user_tone(USER_ID)

        row1 = TONE_OPTIONS[:3]
        row2 = TONE_OPTIONS[3:]

        for i in range(0, len(TONE_OPTIONS), 2):
            row = TONE_OPTIONS[i:i + 2]
            cols = st.columns(len(row))
            for col, tone in zip(cols, row):
                with col:
                    is_active = tone == current_tone
                    if st.button(
                        tone.capitalize(),
                        key=f"tone_{tone}",
                        type="primary" if is_active else "secondary",
                        use_container_width=True,
                    ):
                        if not is_active:
                            set_user_tone(USER_ID, tone)
                            st.rerun()

        st.divider()

        st.markdown("<p class='section-label'>Budget Trackers</p>", unsafe_allow_html=True)
        any_budget = False
        for cat in CATEGORIES:
            limit = get_budget(USER_ID, cat)
            if limit:
                any_budget = True
                spent = get_month_spent(USER_ID, cat)
                from ui.gauges import budget_gauge_bar
                budget_gauge_bar(spent, limit, cat)
        if not any_budget:
            st.caption("No budgets set yet — try 'set food budget to 3000'")

        st.divider()

        display_name = getattr(st.user, "name", None) or st.user.email
        picture = getattr(st.user, "picture", "")
        st.html(f"""
        <div class="profile-row">
          <img src="{picture}" alt="{display_name}" onerror="this.style.display='none'"/>
          <div style="flex:1;min-width:0;">
            <p class="name">{display_name}</p>
            <p class="status">Logged in</p>
          </div>
        </div>
        """)

        if "confirm_clear" not in st.session_state:
            st.session_state.confirm_clear = False

        if not st.session_state.confirm_clear:
            if st.button("🗑️ Clear conversation", use_container_width=True):
                st.session_state.confirm_clear = True
                st.rerun()
        else:
            st.caption("Clear the chat view? Your data is safe either way.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Yes, clear", use_container_width=True, type="primary"):
                    st.session_state.messages = []
                    st.session_state.confirm_clear = False
                    st.rerun()
            with col2:
                if st.button("Cancel", use_container_width=True):
                    st.session_state.confirm_clear = False
                    st.rerun()

        if st.button("Log out", use_container_width=True):
            st.logout()


def handle_user_input(prompt: str) -> str:
    """Runs the agent (or resolves a pending confirmation) and returns the response text."""
    now = time.time()
    if now - st.session_state.request_window_start > 60:
        st.session_state.request_count = 0
        st.session_state.request_window_start = now

    if st.session_state.request_count >= 25:
        return "I'm getting a lot of requests right now — give me about a minute and try again."

    st.session_state.request_count += 1

    if st.session_state.pending_conversion and prompt.replace(".", "", 1).isdigit():
        from db.models import insert_transaction
        from llm.tone import generate_comment
        conv = st.session_state.pending_conversion
        php_amount = float(prompt)
        insert_transaction(USER_ID, prompt, conv["item"], php_amount, conv["category"])
        tone = get_user_tone(USER_ID)
        try:
            comment = generate_comment(conv["item"], php_amount, conv["category"], "PHP", tone)
        except Exception:
            comment = ""
        response = f"Logged: {conv['item']} — ₱{php_amount:.2f} ({conv['category']})"
        if comment:
            response += f"\n\n{comment}"
        st.session_state.pending_conversion = None
        return response

    if st.session_state.pending_edit and prompt.strip().lower() in ("yes", "y", "confirm"):
        edit = st.session_state.pending_edit
        if edit["action"] == "delete":
            from db.models import delete_transaction
            delete_transaction(edit["transaction_id"])
            st.session_state.pending_edit = None
            return "Deleted."
        else:
            from db.models import update_transaction
            update_transaction(edit["transaction_id"], amount=edit["new_amount"], category=edit["new_category"])
            st.session_state.pending_edit = None
            return "Updated!"

    result = run_agent(USER_ID, prompt)
    if result.get("pending_conversion"):
        st.session_state.pending_conversion = result["pending_conversion"]
    if result.get("pending_edit"):
        st.session_state.pending_edit = result["pending_edit"]
    return result["response"]


# --- Main UI ---
def main() -> None:
    st.markdown("""
    <div class="lastna-header">
      <div class="header-brand">
        <div class="header-title-row">
          <h1>Purch.</h1>
          <span class="beta-badge">Beta</span>
        </div>
        <p class="header-tagline">Your last leads to another. Log it. Own it.</p>
      </div>
    </div>
    """, unsafe_allow_html=True)

    render_sidebar()

    if not st.session_state.messages:
        st.html("""
        <div class="empty-state">
            <div class="receipt-icon" style="position:static;display:inline-flex;margin-bottom:1rem;">
                <i class="ti ti-receipt"></i>
            </div>
            <h2>Let's track your spending</h2>
            <p>Tell me what you bought like you're texting a friend — I'll handle the rest.</p>
            <div class="prompt-grid">
                <button disabled>"matcha ₱220"</button>
                <button disabled>"set food budget to 3000"</button>
                <button disabled>"how much did I spend this week"</button>
                <button disabled>"actually that was ₱150"</button>
            </div>
        </div>
        """)
    else:
        for msg in st.session_state.messages:
            render_chat_message(msg)

    prompt = st.chat_input("Tell me what you bought, e.g. 'matcha ₱220'")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar=getattr(st.user, "picture", None) or "🧑"):
            st.markdown(f'<div class="user-bubble"><p>{prompt}</p></div>', unsafe_allow_html=True)

        try:
            response_text = handle_user_input(prompt)
        except Exception as e:
            response_text = f"Something went wrong: {e}"

        with st.chat_message("assistant", avatar="assets/receipt_icon.png"):
            st.write_stream(stream_text(response_text))

        st.session_state.messages.append({"role": "assistant", "content": response_text})
        st.rerun()


if __name__ == "__main__":
    main()