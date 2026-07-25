import streamlit as st


def inject_custom_css():
    """Inject custom CSS for the Purch chat-based budget tracker."""
    st.html(
        """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;600;700&family=Playfair+Display:wght@400;600;700;900&family=Inter:wght@400;500;600;700&display=swap');
  @import url('https://cdn.jsdelivr.net/npm/@tabler/icons-webfont/tabler-icons.min.css');

  /* ============================= TOKENS ============================= */
  :root {
    --mint-white: #F4F7F5;
    --navy: #1B2430;
    --coral: #FF6F59;
    --coral-shadow: rgba(255, 111, 89, 0.2);
    --teal: #2EC4B6;
    --teal-soft: rgba(46, 196, 182, 0.1);
    --amber: #F4A340;
    --red: #E85D5D;
    --white: #FFFFFF;
    --secondary-text: #4A5568;
    --tertiary-text: #718096;
    --border: #E2E8F0;
    --radius-sm: 4px;
    --radius-md: 10px;
    --radius-lg: 16px;
    --shadow-sm: 0 2px 4px rgba(0,0,0,0.05);
    --shadow-md: 0 8px 24px rgba(27,36,48,0.08);
    --shadow-bubble: 0 4px 12px rgba(27,36,48,0.06);
  }

  /* ============================= BASE ============================= */
  html {
    font-size: clamp(14px, 1.5vw, 16px);
  }

  html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    color: var(--navy);
  }

  h1, h2, h3 {
    font-family: 'Fraunces', serif !important;
    color: var(--navy) !important;
    letter-spacing: -0.02em;
  }

  .stApp {
    background-color: var(--mint-white);
  }

  footer {
    display: none !important;
  }

  /* ===================== PAGE / SCROLL BEHAVIOR =====================
     Page itself never scrolls or grows past the viewport. Only the main
     chat column and the sidebar scroll independently, and only once
     their own content actually overflows. */
  html, body {
    height: 100%;
    overflow: hidden;
  }

  [data-testid="stAppViewContainer"] {
    height: 100vh !important;
    overflow: hidden !important;
  }

  section.main {
    height: 100vh !important;
    overflow-y: auto !important;
  }

  section[data-testid="stSidebar"] {
    height: 100vh !important;
    overflow-y: auto !important;
    padding-top: 0 !important;
  }
  section[data-testid="stSidebar"] > div:first-child {
    padding-top: 0rem !important;
  }

  header[data-testid="stHeader"] {
    background: transparent !important;
    height: 3rem !important;
    min-height: 3rem !important;
  }

  .stMainBlockContainer, [data-testid="stMainBlockContainer"] {
    max-width: 1600px !important;
    margin-left: auto !important;
    margin-right: auto !important;
    padding-top: 0.5rem !important;
    padding-left: clamp(1rem, 4vw, 2rem) !important;
    padding-right: clamp(1rem, 4vw, 2rem) !important;
  }

  /* Sidebar collapse control — kept visible/clickable at all times */

  [data-testid="stSidebarCollapsedControl"],
  button[data-testid="stSidebarCollapseButton"],
  [data-testid="collapsedControl"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    color: var(--navy) !important;
    z-index: 9999 !important;
  }
  [data-testid="stSidebarCollapsedControl"] {
    position: fixed !important;
    top: 50vh !important;
    left: 50vw !important;
    z-index: 999999 !important;
    background: red !important;
  }
  [data-testid="stSidebarCollapsedControl"] button,
  button[data-testid="stSidebarCollapseButton"] {
    background: var(--white) !important;
    color: var(--navy) !important;
    border: 0.0625rem solid var(--border) !important;
    border-radius: var(--radius-md) !important;
    box-shadow: var(--shadow-sm) !important;
    width: clamp(2.25rem, 5vw, 2.75rem) !important;
    height: clamp(2.25rem, 5vw, 2.75rem) !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
  }
  [data-testid="stSidebarCollapsedControl"] button:hover,
  button[data-testid="stSidebarCollapseButton"]:hover {
    background: var(--mint-white) !important;
    color: var(--coral) !important;
    border-color: var(--coral) !important;
  }
  [data-testid="stSidebarCollapsedControl"] svg,
  button[data-testid="stSidebarCollapseButton"] svg {
    width: clamp(1.125rem, 2.5vw, 1.375rem) !important;
    height: clamp(1.125rem, 2.5vw, 1.375rem) !important;
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
    color: var(--white) !important;
    border-color: var(--coral) !important;
  }

  .stButton button[kind="secondary"] {
    background-color: var(--white) !important;
    color: var(--navy) !important;
  }
  .stButton button[kind="secondary"]:hover {
    border-color: var(--coral) !important;
    color: var(--coral) !important;
  }

  /* ======================= MAIN RECEIPT HEADER ======================= */
  .lastna-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 0.75rem;
    min-height: 4rem;
    padding: 0.75rem clamp(1rem, 3vw, 1.5rem) 1.25rem clamp(3.5rem, 10vw, 5rem);
    background: var(--white);
    border-radius: 0 0 20px 20px;
    box-shadow: var(--shadow-bubble);
    position: sticky;
    top: 0;
    z-index: 999;
    margin: 0 auto 2rem auto;
    width: 100%;
    max-width: 1400px;
    box-sizing: border-box;
  }
  .lastna-header::after {
    content: "";
    position: absolute;
    bottom: -8px;
    left: 0;
    width: 100%;
    height: 8px;
    background-image:
      linear-gradient(135deg, var(--white) 25%, transparent 25%),
      linear-gradient(225deg, var(--white) 25%, transparent 25%);
    background-position: left bottom;
    background-repeat: repeat-x;
    background-size: 12px 12px;
    filter: drop-shadow(0 4px 2px rgba(27,36,48,0.05));
  }
  .header-brand {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    
  }
  .header-title-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .lastna-header h1 {
    font-family: 'Fraunces', serif !important;
    font-weight: 700 !important;
    font-size: clamp(2rem, 6vw, 2.75rem);
    margin: 0;
    line-height: 1.1;
    letter-spacing: -0.02em;
  }
  .beta-badge {
    display: inline-block;
    padding: 0.2rem 0.45rem;
    background: var(--teal-soft);
    color: var(--teal);
    font-size: clamp(0.55rem, 1.2vw, 0.65rem);
    font-weight: 700;
    border-radius: 6px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-family: 'Inter', sans-serif;
    vertical-align: middle;
  }
  .header-tagline {
    margin: 0;
    font-size: clamp(0.65rem, 1.8vw, 0.85rem);
    color: var(--secondary-text);
    font-family: 'Inter', sans-serif;
    font-style: italic;
    max-width: 100%;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .header-actions {
    display: flex;
    align-items: center;
    gap: 0.35rem;
  }
  .header-actions button {
    background: none;
    border: none;
    cursor: pointer;
    color: var(--secondary-text);
    padding: 0.45rem;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease;
  }
  .header-actions button:hover {
    background: var(--mint-white);
    color: var(--coral);
  }
  .header-actions button i {
    font-size: clamp(1rem, 2.5vw, 1.25rem);
  }

  /* ===================== SIDEBAR MINI RECEIPT HEADER =====================
     Optional: same receipt-notch treatment, sized for the sidebar. Only
     takes effect if you render a `.sidebar-brand` block in the sidebar. */
  .sidebar-brand {
    position: relative;
    margin: -0.5rem -0.5rem 0.75rem -0.5rem;
    padding: 1rem 1.2rem 1.4rem;
    background: var(--white);
    border-bottom: 1px solid var(--border);
    box-shadow: var(--shadow-bubble);
  }
  .sidebar-brand::after {
    content: "";
    position: absolute;
    bottom: -8px;
    left: 0;
    width: 100%;
    height: 6px;
    background-image:
      linear-gradient(135deg, var(--white) 25%, transparent 25%),
      linear-gradient(225deg, var(--white) 25%, transparent 25%);
    background-repeat: repeat-x;
    background-size: 12px 12px;
  }
  .sidebar-brand-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .sidebar-brand h2 {
    margin: 0;
    padding: 0;
    font-family: 'Fraunces', serif;
    font-size: 1.8rem;
    line-height: 1;
  }
  .sidebar-brand .beta-badge {
    margin-top: 0.15rem;
  }

  /* ============================= EMPTY STATE ============================= */
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-start;
    text-align: center;
    padding: clamp(0.5rem, 2vw, 1rem) clamp(1rem, 4vw, 1.5rem) clamp(1rem, 3vw, 1.5rem);
    min-height: 0;
  }
  .empty-state h2 {
    font-size: clamp(3.5rem, 5vw, 2.25rem);
    margin: 0 0 0.5rem 0;
  }
  .empty-state p {
    color: var(--secondary-text);
    font-size: clamp(0.9rem, 2.2vw, 1rem);
    max-width: min(460px, 90vw);
    margin-bottom: 1.25rem;
  }
  .receipt-illustration {
    position: relative;
    margin-bottom: clamp(1.25rem, 4vw, 2rem);
  }
  .receipt-illustration img {
    width: clamp(160px, 40vw, 240px);
    height: clamp(160px, 40vw, 240px);
    object-fit: cover;
    border-radius: clamp(1.5rem, 5vw, 2.5rem);
    box-shadow: var(--shadow-md);
    transform: rotate(3deg);
  }
  .receipt-icon {
    position: absolute;
    bottom: clamp(-0.75rem, -2vw, -1rem);
    right: clamp(-0.75rem, -2vw, -1rem);
    background: var(--white);
    padding: clamp(0.65rem, 2vw, 0.9rem);
    border-radius: clamp(0.75rem, 2vw, 1rem);
    box-shadow: var(--shadow-md);
    border: 1px solid var(--border);
    transform: rotate(-6deg);
  }
  .receipt-icon i {
    font-size: clamp(1.25rem, 4vw, 1.75rem);
    color: var(--coral);
  }
  .prompt-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 0.75rem;
    width: 100%;
    max-width: min(420px, 90vw);
  }
  @media (min-width: 640px) {
    .prompt-grid {
      grid-template-columns: 1fr 1fr;
    }
  }
  .prompt-grid button {
    padding: clamp(0.75rem, 2vw, 0.9rem) clamp(1rem, 3vw, 1.35rem);
    background: var(--white);
    border: 2px solid var(--border);
    border-radius: var(--radius-lg);
    color: var(--navy);
    font-size: clamp(0.75rem, 2vw, 0.85rem);
    font-weight: 700;
    cursor: pointer;
    transition: all 0.2s ease;
    box-shadow: var(--shadow-sm);
    font-family: 'Inter', sans-serif;
  }
  .prompt-grid button:hover {
    border-color: var(--coral);
    color: var(--coral);
  }

 /* ============================= CHAT MESSAGES ============================= */
  .stChatMessage {
    display: flex !important;
    align-items: flex-start !important;
    width: 100% !important;
    max-width: 100% !important;
    background: transparent !important;
    padding: 0 !important;
    margin-bottom: clamp(1.25rem, 3vw, 1.75rem) !important;
    gap: 0.6rem !important;
  }
  .stChatMessage .stChatMessageContent {
    width: 100% !important;
    max-width: 100% !important;
    padding: 0;
  }

  [data-testid="stChatMessageAvatarUser"],
  [data-testid="stChatMessageAvatarAssistant"],
  .stChatMessageAvatar {
    width: 2.5rem !important;
    height: 2.5rem !important;
    min-width: 2.5rem !important;
    min-height: 2.5rem !important;
    border-radius: 50% !important;
    border: 0.125rem solid var(--white) !important;
    box-shadow: var(--shadow-sm) !important;
    background: transparent !important;
    flex-shrink: 0 !important;
    overflow: hidden !important;
    margin: 0 !important;
  }

  [data-testid="stChatMessageAvatarUser"] img,
  [data-testid="stChatMessageAvatarAssistant"] img,
  .stChatMessageAvatar img {
    width: 100% !important;
    height: 100% !important;
    object-fit: cover !important;
  }

  .stChatMessageAvatar > div {
    width: 100% !important;
    height: 100% !important;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 !important;
  }

  .assistant-avatar {
    width: 2.5rem;
    height: 2.5rem;
    border-radius: 50%;
    background: var(--teal);
    display: flex;
    align-items: center;
    justify-content: center;
    border: 0.125rem solid var(--white);
    box-shadow: 0 0 0 0 rgba(46, 196, 182, 0.4);
    animation: avatar-pulse 2s infinite;
  }
  .assistant-avatar i {
    font-size: 1.1rem;
    color: var(--white);
  }
  @keyframes avatar-pulse {
    0% { box-shadow: 0 0 0 0 rgba(46, 196, 182, 0.4); }
    70% { box-shadow: 0 0 0 10px rgba(46, 196, 182, 0); }
    100% { box-shadow: 0 0 0 0 rgba(46, 196, 182, 0); }
  }

  /* Receipt-style bubbles. max-width scales up as viewport grows so
     bubbles use more space on wide screens / collapsed sidebar. */
  .assistant-bubble,
  .user-bubble {
    max-width: min(85%, 700px);
    font-size: clamp(0.875rem, 2.2vw, 0.9375rem);
    line-height: 1.55;
    width: auto;
  }
  @media (min-width: 768px) {
    .assistant-bubble, .user-bubble { max-width: min(760px, calc(100vw - 80px)); }
  }
  @media (min-width: 1200px) {
    .assistant-bubble, .user-bubble { max-width: min(820px, calc(100vw - 400px)); }
  }
  @media (min-width: 1600px) {
    .assistant-bubble, .user-bubble { max-width: 980px; }
  }

  .assistant-bubble {
    position: relative;
    background: var(--white);
    color: var(--navy);
    border-radius: var(--radius-lg) var(--radius-lg) var(--radius-lg) var(--radius-sm);
    padding: clamp(0.9rem, 2.5vw, 1.15rem) clamp(1rem, 3vw, 1.25rem);
    box-shadow: var(--shadow-bubble);
    border: 1px solid var(--border);
  }
  .assistant-bubble::after {
    content: "";
    position: absolute;
    bottom: -8px;
    left: 0;
    width: 100%;
    height: 8px;
    background-image:
      linear-gradient(135deg, var(--white) 25%, transparent 25%),
      linear-gradient(225deg, var(--white) 25%, transparent 25%);
    background-position: left bottom;
    background-repeat: repeat-x;
    background-size: 12px 12px;
    filter: drop-shadow(0 4px 2px rgba(27,36,48,0.03));
  }
  .assistant-bubble.alert-warning { border: 2px solid var(--amber); }
  .assistant-bubble.alert-danger { border: 2px solid var(--red); }
  .assistant-bubble p { margin: 0; }

  .assistant-status {
    margin-top: 0.6rem;
    font-size: clamp(0.6rem, 1.5vw, 0.7rem);
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-family: 'Inter', sans-serif;
  }
  .alert-header {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    margin-bottom: 0.5rem;
    font-family: 'Playfair Display', serif;
    font-weight: 700;
    font-size: clamp(0.55rem, 1.4vw, 0.7rem);
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }

  .user-bubble {
    background: var(--coral);
    color: var(--white);
    border-radius: var(--radius-lg) var(--radius-lg) var(--radius-sm) var(--radius-lg);
    padding: clamp(0.85rem, 2.2vw, 1rem) clamp(1rem, 2.8vw, 1.15rem);
    box-shadow: 0 4px 14px var(--coral-shadow);
  }
  .user-bubble p { margin: 0; }

  /* ============================= CHAT INPUT ============================= */
  .stChatInputContainer {
    background: rgba(244, 247, 245, 0.95) !important;
    backdrop-filter: blur(4px);
    border-top: 1px solid var(--border);
    padding: clamp(0.75rem, 2vw, 1rem) 0;
  }
  .stChatInputContainer > div {
    max-width: 100% !important;
  }
  .stChatInputContainer textarea {
    border-radius: var(--radius-md) !important;
    border: 1px solid var(--border) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: clamp(0.875rem, 2.2vw, 0.9375rem) !important;
    color: var(--navy) !important;
    background: var(--white) !important;
  }
  .stChatInputContainer textarea::placeholder {
    color: var(--tertiary-text) !important;
  }
  .stChatInputContainer button {
    background: var(--coral) !important;
    color: var(--white) !important;
    border-radius: var(--radius-md) !important;
    transition: transform 0.15s ease;
  }
  .stChatInputContainer button:hover {
    transform: translateY(-2px);
  }

  /* ============================= SIDEBAR ============================= */
  section[data-testid="stSidebar"] {
    background-color: var(--mint-white);
    border-left: 1px solid var(--border);
    width: clamp(260px, 28vw, 380px) !important;
    min-width: 0;
  }
  section[data-testid="stSidebar"] > div {
    width: 100% !important;
  }
  section[data-testid="stSidebar"] h1,
  section[data-testid="stSidebar"] h2,
  section[data-testid="stSidebar"] h3 {
    font-family: 'Fraunces', serif;
  }
  section[data-testid="stSidebar"] h2 {
    font-size: 1.9rem !important;
    font-weight: 700 !important;
    margin-bottom: 0.5rem;
    
  }
  section[data-testid="stSidebar"] .stSelectbox > div > div {
    border-radius: var(--radius-md);
    border-color: var(--border);
  }
  [data-testid="stSidebarHeader"] {
    height: 2.5rem !important;
    min-height: 2.5rem !important;
    padding: 0rem 0.5rem !important;
    margin: 0 !important;
    display: flex !important;
    align-items: center !important;
  }

  .section-label {
    font-size: clamp(0.6rem, 1.4vw, 0.7rem);
    font-weight: 800;
    color: var(--tertiary-text);
    text-transform: uppercase;
    letter-spacing: 0.15em;
    margin-bottom: 0.75rem;
    font-family: 'Inter', sans-serif;
  }

  .period-badge {
    display: inline-block;
    font-size: clamp(0.6rem, 1.4vw, 0.7rem);
    font-weight: 700;
    color: var(--teal);
    background: var(--teal-soft);
    padding: 0.2rem 0.5rem;
    border-radius: 6px;
    letter-spacing: 0.02em;
    font-family: 'Inter', sans-serif;
  }

  /* Decorative tone-pill row (non-interactive; real tone buttons are
     rendered separately via st.button) */
  .tone-selector {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    background: var(--mint-white);
    padding: 0.35rem;
    border-radius: var(--radius-md);
    border: 1px solid var(--border);
    margin-bottom: 0.5rem;
  }
  .tone-btn {
    flex: 1 1 auto;
    padding: clamp(0.4rem, 1.5vw, 0.55rem) clamp(0.5rem, 2vw, 0.7rem);
    border-radius: 8px;
    border: none;
    background: transparent;
    color: var(--tertiary-text);
    font-size: clamp(0.65rem, 1.6vw, 0.75rem);
    font-weight: 700;
    cursor: pointer;
    transition: all 0.2s ease;
    text-align: center;
    font-family: 'Inter', sans-serif;
  }
  .tone-btn.active {
    background: var(--white);
    color: var(--navy);
    box-shadow: var(--shadow-sm);
    border: 1px solid var(--border);
  }
  .tone-btn:not(.active):hover {
    background: rgba(255,255,255,0.5);
    color: var(--navy);
  }

  .profile-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 1rem 0.25rem;
    border-top: 1px solid var(--border);
    background: rgba(244, 247, 245, 0.3);
  }
  .profile-row img {
    width: clamp(2rem, 5vw, 2.5rem);
    height: clamp(2rem, 5vw, 2.5rem);
    border-radius: 50%;
    border: 0.125rem solid var(--white);
    box-shadow: var(--shadow-sm);
    object-fit: cover;
  }
  .profile-row .name {
    font-size: clamp(0.8rem, 2vw, 0.9rem);
    font-weight: 700;
    color: var(--navy);
    margin: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .profile-row .status {
    font-size: clamp(0.55rem, 1.4vw, 0.65rem);
    font-weight: 600;
    color: var(--tertiary-text);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin: 0;
  }
  .profile-row button {
    background: none;
    border: none;
    cursor: pointer;
    color: var(--tertiary-text);
    padding: 0.35rem;
    transition: color 0.2s ease;
  }
  .profile-row button:hover { color: var(--red); }
  .profile-row button i { font-size: clamp(1rem, 2.5vw, 1.25rem); }

  /* ============================= SCROLLBAR ============================= */
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 10px; }
  ::-webkit-scrollbar-thumb:hover { background: #CBD5E1; }

  /* ============================= MOBILE ============================= */
  @media (max-width: 768px) {
    .lastna-header {
      flex-direction: column;
      align-items: flex-start;
      min-height: auto;
      padding: 1rem 1.25rem 1.5rem 1.25rem;
    }
    .header-brand { width: 100%; }
    .lastna-header h1 { font-size: 2.1rem !important; }
    .header-tagline {
      white-space: normal;
      overflow: visible;
      text-overflow: unset;
      max-width: 100%;
      font-size: 0.95rem;
      margin-top: 0.25rem;
    }
    .assistant-bubble, .user-bubble { max-width: calc(100vw - 32px); }
    section[data-testid="stSidebar"] { width: 85vw !important; }
  }

  @media (max-width: 480px) {
    .lastna-header h1 { font-size: 1.85rem !important; }
    .header-tagline { font-size: 0.85rem; }
    .header-actions button { padding: 0.35rem; }
  }
</style>
        """
    )