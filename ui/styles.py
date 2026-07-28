import streamlit as st


def inject_custom_css():
    """Inject custom CSS for Purch — Espresso + Coral theme, matching the
    Figma mock exactly."""
    st.html(
        """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;0,700;1,400;1,600&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=DM+Mono:ital,wght@0,300;0,400;0,500;1,400&display=swap');
  @import url('https://cdn.jsdelivr.net/npm/@tabler/icons-webfont/tabler-icons.min.css');

  :root {
    --dark: #1E1410;
    --dark-mid: #2E1E14;
    --coral: #E8573C;
    --coral-light: #FF7A5C;
    --coral-shadow: rgba(232, 87, 60, 0.25);
    --teal: #4DBFB4;
    --teal-soft: rgba(77, 191, 180, 0.12);
    --gold: #F4C55A;
    --parchment: #F7F2EB;
    --paper: #FDF9F4;
    --ink: #1E1410;
    --muted: #9B8F82;
    --border: #E5DDD5;
    --danger: #E63946;

    --mint-white: var(--parchment);
    --navy: var(--ink);
    --secondary-text: #6B5F52;
    --tertiary-text: var(--muted);
    --white: var(--paper);
    --amber: var(--gold);
    --red: var(--danger);
    --radius-sm: 4px;
    --radius-md: 10px;
    --radius-lg: 16px;
    --shadow-sm: 0 2px 4px rgba(30,20,16,0.06);
    --shadow-md: 0 8px 24px rgba(30,20,16,0.1);
    --shadow-bubble: 0 4px 12px rgba(30,20,16,0.08);
    --header-h: 3rem;
  }

  /* ============================= BASE ============================= */
  html { font-size: clamp(14px, 1.5vw, 24px); }

  html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    color: var(--ink);
  }

  h1, h2, h3 {
    font-family: 'Playfair Display', serif !important;
    color: var(--ink) !important;
    letter-spacing: -0.02em;
  }

  .stApp { background-color: var(--parchment); }
  footer { display: none !important; }

  /* ===================== PAGE / SCROLL BEHAVIOR ===================== */
  html, body { height: 100%; overflow: hidden; }
  [data-testid="stAppViewContainer"] { height: 100vh !important; overflow: hidden !important; }
  section.main { height: 100vh !important; overflow-y: auto !important; }
  section[data-testid="stSidebar"] {
    height: 100vh !important;
    overflow-y: auto !important;
    padding-top: 0 !important;
  }
  section[data-testid="stSidebar"] > div:first-child { padding-top: 0 !important; }

  header[data-testid="stHeader"] {
    display: none !important;
  }
  [data-testid="stAppViewContainer"] {
    padding-top: 0 !important;
  }

  .stMainBlockContainer, [data-testid="stMainBlockContainer"] {
    max-width: 1600px !important;
    margin-left: auto !important;
    margin-right: auto !important;
    padding-top: calc(var(--header-h) + 0.5rem) !important;
    padding-left: clamp(1rem, 4vw, 2rem) !important;
    padding-right: clamp(1rem, 4vw, 2rem) !important;
  }

  /* LOGIN PAGE ONLY: the custom app_header isn't rendered pre-login, so
     the block container shouldn't reserve space for it — zero out all
     container padding/max-width whenever our login_page container is
     present anywhere inside it. */
  .stMainBlockContainer:has(.st-key-login_page) {
    padding-top: 0 !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
    padding-bottom: 0 !important;
    max-width: 100% !important;
  }

  /* Sidebar content also starts below the fixed header, regardless of
     collapsed/expanded state, since the header spans the full page width. */
  section[data-testid="stSidebar"] > div:first-child {
    padding-top: calc(var(--header-h) + 0.75rem) !important;
  }

  [data-testid="stSidebarHeader"] {
    height: 2.5rem !important;
    min-height: 2.5rem !important;
    padding: 0 0.5rem !important;
    margin: 0 !important;
    display: flex !important;
    align-items: center !important;
  }

  /* Streamlit's native sidebar collapse control keeps resurfacing across
     versions/reruns, and when it fires it collapses the sidebar through
     its OWN internal mechanism — which our custom toggle (session_state
     + CSS) has no power to undo, causing the "sidebar gone forever" bug.
     display:none alone wasn't enough because some builds re-apply an
     inline style that overrides it. So instead of just hiding it, we push
     it off-screen AND make it unclickable — it can no longer fire, full
     stop, regardless of what display value it gets reset to. */
  [data-testid="stSidebarCollapsedControl"],
  button[data-testid="stSidebarCollapseButton"],
  [data-testid="stExpandSidebarButton"],
  [data-testid="stExpandSidebar"],
  [data-testid="collapsedControl"],
  [data-testid="stSidebarCollapsedControl"] *,
  button[aria-label="Open sidebar"],
  button[aria-label="Close sidebar"],
  button[aria-label*="sidebar" i] {
    position: fixed !important;
    left: -9999px !important;
    top: -9999px !important;
    width: 1px !important;
    height: 1px !important;
    overflow: hidden !important;
    pointer-events: none !important;
    opacity: 0 !important;
  }

  /* ============================= BUTTONS ============================= */
  .stButton button {
    border-radius: var(--radius-md);
    font-weight: 600;
    border: 1px solid var(--border);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    padding-left: 0.5rem !important;
    padding-right: 0.5rem !important;
  }
  section[data-testid="stSidebar"] .stButton button {
    font-size: 0.8rem;
    padding-top: 0.4rem !important;
    padding-bottom: 0.4rem !important;
  }
  .stButton button[kind="primary"] {
    background-color: var(--coral) !important;
    color: #fff !important;
    border-color: var(--coral) !important;
  }
  .stButton button[kind="secondary"] {
    background-color: var(--paper) !important;
    color: var(--ink) !important;
  }
  .stButton button[kind="secondary"]:hover {
    border-color: var(--coral) !important;
    color: var(--coral) !important;
  }

  /* ======================= TOP BAR ==============================
     A real Streamlit container (st.container(key="app_header")),
     fixed + full page width, sitting above the sidebar so it stays put
     whether the sidebar is open or closed. It holds actual st.button
     widgets (sidebar toggle, brand, Analytics/Clear or Back-to-Chat,
     month) — not just static HTML — which is what lets those buttons
     live in the header at all. */
  .st-key-app_header,
  .st-key-app_header > div,
  .st-key-app_header [data-testid="stVerticalBlock"] {
    background: var(--paper) !important;
    background-color: var(--paper) !important;
  }
  .st-key-app_header {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    width: 100%;
    z-index: 1000000;
    border-bottom: 1px solid var(--border);
    box-sizing: border-box;
    height: var(--header-h);
    padding: 0 clamp(0.6rem, 3vw, 1.25rem);
    overflow: hidden;
  }
  /* Streamlit stacks st.columns vertically once the viewport (or the
     column's container query) drops below its own responsive breakpoint —
     that's what was blowing the fixed header up to full-page height on
     mobile. The header must never do that, so row layout + no-wrap are
     forced at every width, overriding Streamlit's own responsive rules. */
  .st-key-app_header [data-testid="stHorizontalBlock"] {
    align-items: center !important;
    justify-content: flex-start !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    gap: clamp(0.25rem, 1.5vw, 0.5rem) !important;
    height: 100%;
  }
  .st-key-app_header [data-testid="stColumn"] {
    display: flex !important;
    align-items: center !important;
    justify-content: center;
    height: 100%;
    min-width: 0 !important;
    width: auto !important;
  }
  .st-key-app_header [data-testid="stColumn"] > div {
    width: 100%;
    display: flex !important;
    align-items: center !important;
    height: 100%;
    min-width: 0 !important;
  }
  .st-key-app_header .stMarkdown {
    margin: 0 !important;
  }
  /* The Analytics/Clear (or Cancel/Confirm) pair is a nested st.columns
     inside c_actions — force that inner row horizontal too, with its own
     tight gap independent of the outer header gap. */
  .st-key-app_header [data-testid="stColumn"] [data-testid="stHorizontalBlock"] {
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    gap: 0.3rem !important;
    width: auto !important;
  }
  .st-key-app_header [data-testid="stColumn"] [data-testid="stColumn"] {
    width: auto !important;
    min-width: 0 !important;
  }
  .st-key-sidebar_toggle_btn button {
    font-size: 1rem !important;
    padding: 0.3rem 0.5rem !important;
    line-height: 1 !important;
    min-width: 2rem;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: var(--muted) !important;
  }
  .st-key-sidebar_toggle_btn button:hover {
    color: var(--coral) !important;
    background: transparent !important;
  }
  .st-key-app_header .stButton button {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    padding: 0.3rem 0.5rem !important;
    border-radius: var(--radius-md) !important;
    background: transparent !important;
    border: none !important;
    color: var(--muted) !important;
    box-shadow: none !important;
  }
  .st-key-app_header .stButton button:hover {
    background: transparent !important;
    color: var(--coral) !important;
  }
  /* Analytics + Clear: compact icon-only buttons (tooltip carries the
     label via st.button(help=...)) so this pair stays minimal at any
     header width instead of reserving space for text. */
  .st-key-hdr_analytics_btn button,
  .st-key-hdr_clear_btn button {
    font-size: 1rem !important;
    line-height: 1 !important;
    padding: 0.25rem 0.4rem !important;
    min-width: 1.85rem;
    background: transparent !important;
    border: none !important;
    color: var(--muted) !important;
    box-shadow: none !important;
  }
  .st-key-hdr_analytics_btn button:hover,
  .st-key-hdr_clear_btn button:hover {
    background: transparent !important;
    color: var(--coral) !important;
  }
  /* Confirm keeps its coral "primary" emphasis for the destructive step */
  .st-key-hdr_confirm_clear_btn button[kind="primary"] {
    background: var(--coral) !important;
    border: none !important;
    color: #fff !important;
  }
  .st-key-hdr_cancel_clear_btn button,
  .st-key-hdr_back_btn button {
    border: 1px solid var(--border) !important;
    color: var(--ink) !important;
    font-size: 0.8rem !important;
    padding: 0.3rem 0.6rem !important;
  }
  .header-brand-wrapper {
    height: 100%;
    display: flex;
    align-items: center;
  }
  .header-brand {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    white-space: nowrap;
  }
  .header-brand-text {
    font-family: 'Playfair Display', serif;
    font-weight: 700;
    font-size: 1.25rem;
    line-height: 1;
    color: var(--ink);
  }
  .header-month {
    font-family: 'DM Mono', monospace;
    font-size: 0.65rem;
    color: var(--muted);
    opacity: 0.6;
    white-space: nowrap;
  }
  .beta-badge {
    display: inline-block;
    padding: 0.15rem 0.4rem;
    background: var(--teal-soft);
    color: var(--teal);
    font-size: 0.6rem;
    font-weight: 700;
    border-radius: 6px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-family: 'Plus Jakarta Sans', sans-serif;
    vertical-align: middle;
  }

  /* ============================= LOGIN SCREEN ============================= */

  /* Real Streamlit container (st.container(key="login_page")) that wraps
     a two-column st.columns layout, so the "Continue with Google" button
     can be an actual widget sitting physically below the login card in
     the right-hand column. */
  .st-key-login_page {
    width: 100vw;
    height: 100vh;
    margin-left: calc(50% - 50vw);
    margin-right: calc(50% - 50vw);
    overflow: hidden;
  }
  .st-key-login_page [data-testid="stHorizontalBlock"] {
    height: 100vh;
    gap: 0 !important;
    align-items: stretch !important;
  }
  .st-key-login_page [data-testid="stColumn"] {
    height: 100vh;
    padding: 0 !important;
  }

  /* LEFT SECTION */
  .st-key-login_left_col {
    height: 100vh;
    background: var(--dark);
    padding: clamp(1.5rem, 4vh, 3rem) clamp(1.5rem, 5vw, 5rem);
    box-sizing: border-box;
    overflow: hidden;
  }
  .st-key-login_left_col [data-testid="stVerticalBlock"] {
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
  }
  .st-key-login_left_col .stMarkdown:first-child {
    margin-bottom: clamp(0.75rem, 2vh, 1.5rem);
  }

  /* RIGHT SECTION */
  .st-key-login_right_col {
    height: 100vh;
    background: var(--parchment);
    padding: clamp(2rem, 5vw, 4rem) clamp(1.5rem, 6vw, 6rem);
    box-sizing: border-box;
    overflow: hidden;
  }
  .st-key-login_right_col [data-testid="stVerticalBlock"] {
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    gap: 0.7rem;
  }

  /* BRAND */
  .login-brand {
    font-family: 'Playfair Display', serif;
    font-size: clamp(1.75rem, 2vw, 2.25rem);
    font-weight: 700;
    color: var(--gold);
  }

  /* HEADLINE */
  .login-headline {
    font-family: 'Playfair Display', serif;
    font-weight: 700;
    font-size: clamp(3rem, 7vw, 5.25rem);
    line-height: 1.02;
    color: var(--parchment) !important;
    margin: 0 0 0.75rem 0;
  }
  .login-headline em {
    font-style: italic;
    color: var(--coral-light);
  }

  .login-eyebrow {
    font-family: 'DM Mono', monospace;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--gold);
    line-height: 1.2;
    margin-bottom: 0.35rem;
  }

  .login-sub {
    font-size: clamp(1rem, 1.1vw, 1.15rem);
    line-height: 1.7;
    max-width: 480px;
    color: var(--muted);
    margin-bottom: 0.5rem;
  }

  /* TONE TAGS */
  .login-tones {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
  }
  .login-tone-chip {
    padding: 0.25rem 0.6rem;
    border-radius: 999px;
    font-size: 0.65rem;
    font-weight: 500;
    background: var(--dark-mid);
    color: var(--muted);
  }

  /* LOGIN PREVIEW */
  .login-preview-card {
    width: 100%;
    border-radius: 20px;
    overflow: hidden;
    box-shadow: var(--shadow-md);
    border: 1px solid var(--border);
    margin-bottom: 1rem;
  }
  .login-preview-topbar {
    background: var(--dark);
    padding: 0.6rem 1rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .login-preview-body {
    background: var(--paper);
    padding: 1rem;
  }
  .login-preview-user-msg {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 0.6rem;
  }
  .login-preview-assistant-msg {
    display: flex;
    align-items: flex-start;
    gap: 0.4rem;
    margin-bottom: 0.6rem;
  }

  /* LOGIN CARD */
  .login-card {
    background: var(--paper);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 0.5rem 1.35rem;
    margin-bottom: 1.5rem;
    width: 100%;
  }
  .login-card h2 {
    font-family: 'Playfair Display', serif;
    font-weight: 700;
    font-size: 1.4rem;
    line-height: 0.5rem;
    margin: 0 0 0.25rem 0;
  }
  .login-card p {
    font-size: 0.85rem;
    line-height: 0.5rem;
    color: var(--muted);
    margin: 0 0 1.25rem 0;
  }

  .st-key-login_google_btn {
    display: flex;
    justify-content: center;
    width: 100%;
  }
  .st-key-login_google_btn button {
    min-height: 44px !important;
    height: 44px !important;
    font-size: 0.9rem !important;
    padding: 0.7rem 1rem !important;
    width: 100% !important;
  }

  /* ============================= EMPTY STATE (chat) ============================= */
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-start;
    text-align: center;
    padding: clamp(2rem, 8vw, 3rem) 1rem;
    min-height: 0;
  }
  .empty-state-badge {
    --badge-size: clamp(3rem, 5vw, 5rem);
    width: var(--badge-size);
    height: var(--badge-size);
    border-radius: calc(var(--badge-size) * 0.27);
    background: var(--dark);
    color: var(--gold);
    font-family: 'Playfair Display', serif;
    font-size: calc(var(--badge-size) * 0.38);
    font-weight: 700;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 1rem;
  }
  .empty-state h3 {
    font-family: 'Playfair Display', serif;
    font-weight: 700;
    font-size: 1.2rem;
    color: var(--ink);
    margin: 0 0 6px 0;
  }
  .empty-state p {
    font-size: 0.85rem;
    color: var(--muted);
    line-height: 1.6;
    max-width: 320px;
    margin: 0 auto 1.25rem auto;
  }
  .prompt-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 0.6rem;
    width: 100%;
    max-width: min(420px, 90vw);
  }
  @media (min-width: 640px) { .prompt-grid { grid-template-columns: 1fr 1fr; } }
  .prompt-grid button {
    padding: 0.6rem 1rem;
    background: var(--paper);
    border: 1px solid var(--border);
    border-radius: 999px;
    color: var(--ink);
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    font-family: 'Plus Jakarta Sans', sans-serif;
  }
  .prompt-grid button:hover { border-color: var(--coral); color: var(--coral); }

  /* ============================= CHAT BUBBLES ============================= */
  .assistant-bubble, .user-bubble {
    font-size: clamp(0.875rem, 2.2vw, 0.9375rem);
    line-height: 1.55;
  }
  .assistant-bubble {
    position: relative;
    background: var(--paper);
    color: var(--ink);
    border-radius: var(--radius-lg) var(--radius-lg) var(--radius-lg) var(--radius-sm);
    padding: 0.9rem 1.1rem;
    box-shadow: var(--shadow-bubble);
    border: 1px solid var(--border);
  }
  .assistant-bubble.alert-warning { border: 2px solid var(--gold); }
  .assistant-bubble.alert-danger { border: 2px solid var(--danger); }
  .assistant-bubble p { margin: 0; }
  .alert-header {
    display: flex; align-items: center; gap: 0.35rem; margin-bottom: 0.5rem;
    font-family: 'Playfair Display', serif; font-weight: 700;
    font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.1em;
  }
  .user-bubble {
    background: var(--dark);
    color: var(--parchment);
    border-radius: var(--radius-lg) var(--radius-lg) var(--radius-sm) var(--radius-lg);
    padding: 0.85rem 1.1rem;
    box-shadow: 0 4px 14px rgba(30,20,16,0.18);
  }
  .user-bubble p { margin: 0; }

  /* ============================= CHAT INPUT ============================= */
  .stChatInputContainer {
    background: rgba(247, 242, 235, 0.95) !important;
    backdrop-filter: blur(4px);
    border-top: 1px solid var(--border);
    padding: clamp(0.75rem, 2vw, 1rem) 0;
  }
  .stChatInputContainer textarea {
    border-radius: var(--radius-md) !important;
    border: 1px solid var(--border) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    color: var(--ink) !important;
    background: var(--paper) !important;
  }
  .stChatInputContainer textarea::placeholder { color: var(--muted) !important; }
  .stChatInputContainer button {
    background: var(--coral) !important;
    color: #fff !important;
    border-radius: var(--radius-md) !important;
  }

  /* ============================= SIDEBAR ============================= */
  section[data-testid="stSidebar"] {
    background-color: var(--parchment);
    border-left: 1px solid var(--border);
    width: clamp(260px, 28vw, 380px) !important; 
    min-width: clamp(0px, 28vw, 380px) !important;
  }
  section[data-testid="stSidebar"] > div { width: 100% !important; }
  section[data-testid="stSidebar"] h1,
  section[data-testid="stSidebar"] h2,
  section[data-testid="stSidebar"] h3 { font-family: 'Playfair Display', serif; }
  section[data-testid="stSidebar"] h2 {
    font-size: 1.25rem !important;
    font-weight: 700 !important;
    margin: 0.4rem 0 1rem 0 !important;
  }
  section[data-testid="stSidebar"] .stSelectbox > div > div {
    border-radius: var(--radius-md);
    border-color: var(--border);
  }
  .section-label {
    font-size: 0.6rem;
    font-weight: 600;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.6rem;
    font-family: 'DM Mono', monospace;
  }
  .profile-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 1rem 0.25rem;
    border-top: 1px solid var(--border);
  }
  .profile-row img {
    width: 2.25rem; height: 2.25rem; border-radius: 50%;
    border: 2px solid var(--paper); box-shadow: var(--shadow-sm); object-fit: cover;
  }
  .profile-row .name {
    font-size: 0.85rem; font-weight: 700; color: var(--ink); margin: 0;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .profile-row .status {
    font-size: 0.6rem; font-weight: 600; color: var(--muted);
    text-transform: uppercase; letter-spacing: 0.05em; margin: 0;
  }
  .total-budget-card {
    background: var(--dark);
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 1rem;
  }
  .total-budget-card .label {
    font-family: 'DM Mono', monospace; font-size: 0.6rem; font-weight: 500;
    text-transform: uppercase; letter-spacing: 0.06em; color: #C4B8A8; margin-bottom: 6px;
  }
  .total-budget-card .amount {
    font-family: 'DM Mono', monospace; font-size: 1.5rem; font-weight: 700; color: var(--gold); margin-bottom: 0.6rem;
  }
  .total-budget-card .track { background: var(--dark-mid); border-radius: 6px; height: 6px; overflow: hidden; }
  .total-budget-card .fill { height: 100%; border-radius: 6px; background: linear-gradient(90deg, var(--coral), var(--gold)); }
  .total-budget-card .foot { display: flex; justify-content: space-between; margin-top: 4px; font-size: 0.6rem; color: #C4B8A8; }

  /* ============================= SCROLLBAR ============================= */
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 10px; }
  ::-webkit-scrollbar-thumb:hover { background: #D6C8B8; }

  /* ============================= MOBILE ============================= */
  @media (max-width: 768px) {
    :root { --header-h: 2.75rem; }

    /* Header stays one row (forced above) — this just tightens it further
       so toggle + brand + actions + month all fit comfortably. */
    .st-key-app_header { padding: 0 0.5rem; }
    .header-brand-text { font-size: 0.95rem; }
    .beta-badge { padding: 0.1rem 0.3rem; font-size: 0.55rem; }
    .header-month { display: none; }
    .st-key-sidebar_toggle_btn button { padding: 0.25rem 0.4rem !important; }
    .st-key-hdr_analytics_btn button,
    .st-key-hdr_clear_btn button { min-width: 1.6rem; padding: 0.2rem 0.3rem !important; }
    .st-key-hdr_back_btn button,
    .st-key-hdr_cancel_clear_btn button,
    .st-key-hdr_confirm_clear_btn button { font-size: 0.72rem !important; padding: 0.25rem 0.5rem !important; }

    /* Login page: panels stack top-to-bottom instead of side-by-side. */
    .st-key-login_page [data-testid="stHorizontalBlock"] { flex-direction: column !important; height: auto; }
    .st-key-login_page { height: auto; min-height: 100vh; overflow: visible; }
    .st-key-login_left_col,
    .st-key-login_right_col { height: auto; min-height: 50vh; }
    .st-key-login_left_col { padding: 1.5rem 1.25rem; }
    .st-key-login_right_col { padding: 1.75rem 1.25rem; }
    .login-headline { font-size: clamp(2.25rem, 9vw, 3rem); }

    /* Sidebar + content: reclaim space on narrow screens. */
    section[data-testid="stSidebar"] {
      width: 88vw !important;
      min-width: 88vw !important;
    }
    section[data-testid="stSidebar"] > div:first-child { padding-left: 0.75rem !important; padding-right: 0.75rem !important; }
    .stMainBlockContainer, [data-testid="stMainBlockContainer"] {
      padding-left: 0.75rem !important;
      padding-right: 0.75rem !important;
    }
    .assistant-bubble, .user-bubble { padding: 0.75rem 0.9rem; }
    .empty-state { padding: 1.5rem 0.75rem; }
  }

  @media (max-width: 420px) {
    .header-brand-text { font-size: 0.85rem; }
    .beta-badge { display: none; }
  }
</style>
        """
    )