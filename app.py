"""Purch — chat-based budget tracker."""
import time
from datetime import date, datetime
import streamlit as st

from db.connection import init_db, ensure_user
from db.models import get_user_tone, set_user_tone, get_all_budgets_and_spending
from llm.extraction import CATEGORIES
from llm.tone import VALID_TONES
from agent.graph import run_agent
from ui.styles import inject_custom_css

RECEIPT_ICON = "assets/receipt_icon.png"

st.set_page_config(
    page_title="Purch",
    page_icon=RECEIPT_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

TONE_SAMPLES = {
    "nonchalant": "Logged: Milk tea ₱85.",
    "bestie": "Yay! Milk tea ₱85 saved! 🧋",
    "sarcastic": "Oh wow, another milk tea. ₱85.",
    "coach": "Logged ₱85. Stay on track!",
    "rich tita": "Anak, ₱85 for milk tea? Noted.",
    "kapampangan": "Sige, ₱85. Mangan na tamu!",
}

TONE_EMOJI = {
    "nonchalant": "🤍",
    "bestie": "✨",
    "sarcastic": "🙄",
    "coach": "💪",
    "rich tita": "💅",
    "kapampangan": "🍖",
}

CATEGORY_EMOJI = {
    "Food": "🍽️",
    "Transport": "🚌",
    "Bills": "🧾",
    "Shopping": "🛍️",
    "Entertainment": "🎮",
    "Health": "❤️",
    "Personal Care": "🧴",
    "Other": "🗂️",
}

# --- Auth gate — matches the two-panel login screen from the mock.
# Built as real st.columns()/st.container() rather than one raw flex div
# so the "Continue with Google" button can be an actual Streamlit widget
# sitting physically below the login card in the right-hand column.
if not st.user.is_logged_in:
    inject_custom_css()

    with st.container(key="login_page"):
        col_left, col_right = st.columns([1, 1], gap="small")

        with col_left:
            with st.container(key="login_left_col"):
                st.markdown(
                    '<div class="login-brand">Purch</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(f"""
                <div>
                  <div class="login-eyebrow">Budget tracking, reimagined</div>
                  <h1 class="login-headline">Your last<br><em>eventually</em><br>leads to<br>another.</h1>
                  <p class="login-sub">Log expenses the way you text — casually. Purch extracts the rest.</p>
                  <div class="login-tones">
                    {''.join(f'<span class="login-tone-chip">{t.capitalize()}</span>' for t in VALID_TONES)}
                  </div>
                  <p style="font-size:0.7rem; color:var(--muted); line-height:3;">{len(VALID_TONES)} personality tones — including Tita and Kapampangan</p>
                </div>
                """, unsafe_allow_html=True)

        with col_right:
            with st.container(key="login_right_col"):
                st.markdown("""
                <div class="login-preview-card">
                  <div class="login-preview-topbar">
                    <span style="font-size:0.7rem; color:var(--gold); font-family:'DM Mono',monospace;">PURCH RECEIPT</span>
                    <span style="font-size:0.7rem; color:var(--muted); font-family:'DM Mono',monospace;">✨ Bubbly</span>
                  </div>
                  <div class="login-preview-body">
                    <div class="login-preview-user-msg">
                      <div class="user-bubble" style="max-width:80%; font-size:0.75rem; padding:0.5rem 0.75rem;">
                        bought a phone case for 350
                      </div>
                    </div>
                    <div class="login-preview-assistant-msg">
                      <div style="width:1.5rem;height:1.5rem;border-radius:50%;background:var(--dark);color:var(--gold);display:flex;align-items:center;justify-content:center;font-family:'Playfair Display',serif;font-weight:700;font-size:0.7rem;flex-shrink:0;">
                        P
                      </div>
                      <div class="assistant-bubble" style="max-width:80%; font-size:0.75rem; padding:0.5rem 0.75rem;">
                        Logged! Phone case ₱350 under Shopping. 🛍️
                      </div>
                    </div>
                    <div class="login-preview-user-msg">
                      <div class="user-bubble" style="max-width:80%; font-size:0.75rem; padding:0.5rem 0.75rem;">
                        how much did i spend this week?
                      </div>
                    </div>
                    <div class="login-preview-assistant-msg">
                      <div style="width:1.5rem;height:1.5rem;border-radius:50%;background:var(--dark);color:var(--gold);display:flex;align-items:center;justify-content:center;font-family:'Playfair Display',serif;font-weight:700;font-size:0.7rem;flex-shrink:0;">
                        P
                      </div>
                      <div class="assistant-bubble" style="max-width:80%; font-size:0.75rem; padding:0.5rem 0.75rem;">
                        You spent ₱2,450 this week. Most went to Food. 🍽️
                      </div>
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("""
                <div class="login-card">
                  <h2>Own it. Log it.</h2>
                  <p>Sign in to start tracking the way you actually talk.</p>
                </div>
                """, unsafe_allow_html=True)

                with st.container(key="login_google_btn"):
                    if st.button("Continue with Google", use_container_width=True, type="primary"):
                        st.login()
    st.stop()

USER_ID = st.user.email
init_db()
ensure_user(USER_ID)
inject_custom_css()

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
if "confirm_clear" not in st.session_state:
    st.session_state.confirm_clear = False
if "screen" not in st.session_state:
    st.session_state.screen = "chat"
if "sidebar_open" not in st.session_state:
    st.session_state.sidebar_open = True


def nav(screen: str) -> None:
    st.session_state.screen = screen
    st.rerun()


def now_str() -> str:
    return datetime.now().strftime("%I:%M %p")


def classify_alert(text: str) -> str:
    lower = text.lower()
    if "over your" in lower and "budget" in lower:
        return "danger"
    if "heads up" in lower or "almost" in lower:
        return "warning"
    return ""


def chat_bubble_html(role: str, text: str, meta: str, time_str: str) -> str:
    content_html = text.replace("\n", "<br>")

    if role == "user":
        return f"""
        <div style="display:flex; justify-content:flex-end; margin-bottom:1rem;">
          <div style="max-width:75%; display:flex; flex-direction:column; align-items:flex-end;">
            <div class="user-bubble"><p>{content_html}</p></div>
            <div style="font-size:0.65rem; color:var(--muted); margin-top:4px; margin-right:2px;">{time_str}</div>
          </div>
        </div>
        """

    alert = classify_alert(text)
    alert_class = f" alert-{alert}" if alert else ""
    alert_html = ""
    if alert == "danger":
        alert_html = '<div class="alert-header" style="color:var(--red);"><i class="ti ti-alert-triangle-filled"></i><span>Over Budget</span></div>'
    elif alert == "warning":
        alert_html = '<div class="alert-header" style="color:var(--amber);"><i class="ti ti-alert-triangle-filled"></i><span>Budget Warning</span></div>'

    meta_html = ""
    if meta:
        meta_html = (
            f'<div style="margin-top:8px; padding-top:8px; font-size:11px; '
            f'border-top:1px dashed var(--border); color:var(--muted); '
            f'font-family:\'DM Mono\',monospace;">{meta}</div>'
        )

    return f"""
    <div style="display:flex; justify-content:flex-start; margin-bottom:1rem;">
      <div style="width:2rem; height:2rem; border-radius:50%; background:var(--dark);
                  color:var(--gold); display:flex; align-items:center; justify-content:center;
                  font-family:'Playfair Display',serif; font-weight:700; font-size:0.9rem;
                  margin-right:0.5rem; flex-shrink:0; margin-top:2px;">P</div>
      <div style="max-width:75%;">
        <div class="assistant-bubble{alert_class}">{alert_html}<p>{content_html}</p>{meta_html}</div>
        <div style="font-size:0.65rem; color:var(--muted); margin-top:4px; margin-left:2px;">{time_str}</div>
      </div>
    </div>
    """


def total_budget_card_html(spent: float, limit: float, month_label: str) -> str:
    pct_val = min(round((spent / limit) * 100), 100) if limit else 0
    return f"""
    <div class="total-budget-card">
      <div class="label">{month_label} — Total</div>
      <div class="amount">₱{spent:,.0f}</div>
      <div class="track"><div class="fill" style="width:{pct_val}%;"></div></div>
      <div class="foot"><span>{pct_val}%</span><span>₱{limit:,.0f}</span></div>
    </div>
    """


def render_sidebar(screen: str) -> None:
    with st.sidebar:
        budget_data = get_all_budgets_and_spending(USER_ID, CATEGORIES)
        total_spent = sum(d["spent"] for d in budget_data.values())
        total_limit = sum(d["limit"] or 0 for d in budget_data.values())

        if total_limit > 0:
            st.markdown(
                total_budget_card_html(total_spent, total_limit, date.today().strftime("%B %Y")),
                unsafe_allow_html=True,
            )

        st.markdown("<p class='section-label'>Budgets</p>", unsafe_allow_html=True)
        any_budget = False
        for cat in CATEGORIES:
            data = budget_data[cat]
            if data["limit"]:
                any_budget = True
                pct_val = min(round((data["spent"] / data["limit"]) * 100), 100)
                over = data["spent"] > data["limit"]
                color = "var(--danger)" if over else "var(--coral)"
                warn = " ⚠️" if over else ""
                icon = CATEGORY_EMOJI.get(cat, "🗂️")
                st.markdown(f"""
                <div style="margin-bottom:0.7rem;">
                  <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.71rem; margin-bottom:3px;">
                    <span style="color:var(--ink); font-weight:500;">{icon} {cat}{warn}</span>
                    <span style="font-family:'DM Mono',monospace; font-size:0.69rem; color:{color};">₱{data['spent']:,.0f}</span>
                  </div>
                  <div style="height:5px; background:var(--border); border-radius:4px; overflow:hidden;">
                    <div style="height:100%; width:{pct_val}%; background:{color}; border-radius:4px;"></div>
                  </div>
                  <div style="display:flex; justify-content:space-between; margin-top:2px;">
                    <span style="font-size:0.6rem; color:var(--muted);">{pct_val}%</span>
                    <span style="font-size:0.6rem; color:var(--muted);">₱{data['limit']:,.0f}</span>
                  </div>
                </div>
                """, unsafe_allow_html=True)
        if not any_budget:
            st.caption("No budgets set yet — try 'set food budget to 3000'")

        st.divider()

        st.markdown("<p class='section-label'>Tone</p>", unsafe_allow_html=True)
        current_tone = get_user_tone(USER_ID)
        new_tone = st.selectbox(
            "Tone",
            options=TONE_OPTIONS,
            index=TONE_OPTIONS.index(current_tone),
            format_func=lambda t: f"{TONE_EMOJI.get(t, '')} {t.capitalize()}",
            label_visibility="collapsed",
        )
        if new_tone != current_tone:
            set_user_tone(USER_ID, new_tone)
            st.rerun()

        sample = TONE_SAMPLES.get(current_tone, "")
        if sample:
            st.markdown(
                f'<div style="font-size:0.72rem; color:var(--muted); margin-top:6px; line-height:1.5;">"{sample}"</div>',
                unsafe_allow_html=True,
            )

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

        if st.button("Log out", use_container_width=True):
            st.logout()


def handle_user_input(prompt: str):
    now = time.time()
    if now - st.session_state.request_window_start > 60:
        st.session_state.request_count = 0
        st.session_state.request_window_start = now

    if st.session_state.request_count >= 25:
        return "I'm getting a lot of requests right now — give me about a minute and try again.", ""

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
        return response, f"{conv['category']} • ₱{php_amount:.0f} • Today"

    if st.session_state.pending_edit and prompt.strip().lower() in ("yes", "y", "confirm"):
        edit = st.session_state.pending_edit
        if edit["action"] == "delete":
            from db.models import delete_transaction
            delete_transaction(edit["transaction_id"])
            st.session_state.pending_edit = None
            return "Deleted.", ""
        else:
            from db.models import update_transaction
            update_transaction(edit["transaction_id"], amount=edit["new_amount"], category=edit["new_category"])
            st.session_state.pending_edit = None
            return "Updated!", ""

    result = run_agent(USER_ID, prompt)
    if result.get("pending_conversion"):
        st.session_state.pending_conversion = result["pending_conversion"]
    if result.get("pending_edit"):
        st.session_state.pending_edit = result["pending_edit"]

    meta = ""
    if result.get("transaction_id") and result.get("category") and result.get("amount"):
        meta = f"{result['category']} • ₱{result['amount']:.0f} • Today"

    return result["response"], meta


def render_header(screen: str) -> None:
    """Fixed, full-width top bar — sits above the sidebar so it stays put
    whether the sidebar is open or closed. Built as a real Streamlit
    container (not static HTML) so it can hold working widgets: the
    sidebar open/close toggle, and the Analytics/Clear actions."""
    with st.container(key="app_header"):
        # A flexible spacer column between brand and the right-side controls
        # is what pushes "Purch" to the far left and the action buttons to
        # the far right — st.columns divides the full header width by these
        # ratios, so a wide spacer eats the middle instead of the actions
        # column sitting in the middle of the row.
        c_toggle, c_brand, c_spacer, c_actions, c_month = st.columns(
            [0.4, 2.0, 4.5, 1.4, 0.6], vertical_alignment="center"
        )

        with c_toggle:
            toggle_icon = "✕" if st.session_state.sidebar_open else "☰"
            if st.button(toggle_icon, key="sidebar_toggle_btn"):
                st.session_state.sidebar_open = not st.session_state.sidebar_open
                st.rerun()

        with c_brand:
            st.markdown(
                """
                <div class="header-brand-wrapper">
                  <div class="header-brand">
                    <span class="header-brand-text">Purch</span>
                    <span class="beta-badge">Beta</span>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Analytics/Clear (or Back / Cancel-Confirm) live inside their own
        # tightly-gapped nested columns, independent of the header's overall
        # column gap — that's what keeps this pair compact regardless of
        # viewport width.
        with c_actions:
            if screen == "chat":
                if not st.session_state.confirm_clear:
                    a1, a2 = st.columns([1, 1], gap="small")
                    with a1:
                        if st.button("↗ Analytics", key="hdr_analytics_btn", help="Analytics"):
                            nav("analytics")
                    with a2:
                        if st.button("↺ Clear", key="hdr_clear_btn", help="Clear chat"):
                            st.session_state.confirm_clear = True
                            st.rerun()
                else:
                    a1, a2 = st.columns([1, 1], gap="small")
                    with a1:
                        if st.button("Cancel", key="hdr_cancel_clear_btn", use_container_width=True):
                            st.session_state.confirm_clear = False
                            st.rerun()
                    with a2:
                        if st.button("Confirm", key="hdr_confirm_clear_btn", use_container_width=True, type="primary"):
                            st.session_state.messages = []
                            st.session_state.confirm_clear = False
                            st.rerun()
            else:
                if st.button("Back to Chat", key="hdr_back_btn", use_container_width=True):
                    nav("chat")

        with c_month:
            st.markdown(
                f'<div class="header-month" style="text-align:right;">'
                f'{datetime.now().strftime("%b %Y")}</div>',
                unsafe_allow_html=True,
            )


def page_chat() -> None:
    chat_area = st.container()
    with chat_area:
        if not st.session_state.messages:
            st.markdown("""
            <div class="empty-state">
              <div class="empty-state-badge">P</div>
              <h3>Hey! I'm Purch.</h3>
              <p>Just type what you bought and I'll handle the rest. No forms, no dropdowns — just chat.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            for msg in st.session_state.messages:
                st.markdown(
                    chat_bubble_html(msg["role"], msg["text"], msg.get("meta", ""), msg["time"]),
                    unsafe_allow_html=True,
                )

    prompt = st.chat_input(placeholder='Try "milk tea ₱85" or "how much this week?"')
    if prompt:
        ts = now_str()
        st.session_state.messages.append({"role": "user", "text": prompt, "meta": "", "time": ts})

        try:
            response_text, meta = handle_user_input(prompt)
        except Exception as e:
            response_text, meta = f"Something went wrong: {e}", ""

        st.session_state.messages.append({"role": "assistant", "text": response_text, "meta": meta, "time": ts})
        st.rerun()


def page_analytics() -> None:
    """Stub analytics screen — proves out the nav wiring. Real charts
    (trend / breakdown / compare, per the mock) land here next, backed by
    new db/models.py query functions."""
    st.markdown(f"""
    <div style="margin:0 0 1.25rem 0; padding:0 0.25rem;">
      <div style="font-family:'DM Mono',monospace; font-size:0.65rem; font-weight:500;
                  text-transform:uppercase; letter-spacing:0.1em; color:var(--muted); margin-bottom:4px;">
        Spending Overview
      </div>
      <div style="font-family:'Playfair Display',serif; font-weight:700; font-size:1.75rem; color:var(--ink);">
        {date.today().strftime('%B %Y')}
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="background:var(--paper); border:1px solid var(--border); border-radius:16px;
                padding:3rem 1.5rem; text-align:center;">
      <div style="font-size:2rem; margin-bottom:0.5rem;">📊</div>
      <div style="font-family:'Playfair Display',serif; font-weight:700; font-size:1.1rem;
                  color:var(--ink); margin-bottom:4px;">
        Analytics coming soon
      </div>
      <div style="font-size:0.85rem; color:var(--muted); max-width:360px; margin:0 auto;">
        Trend, category breakdown, and month-over-month comparisons will land here next.
      </div>
    </div>
    """, unsafe_allow_html=True)


def main() -> None:
    screen = st.session_state.screen
    render_header(screen)

    if not st.session_state.sidebar_open:
        st.markdown(
            "<style>section[data-testid='stSidebar']{display:none !important;}</style>",
            unsafe_allow_html=True,
        )
    else:
        render_sidebar(screen)

    if screen == "analytics":
        page_analytics()
    else:
        page_chat()


if __name__ == "__main__":
    main()
