# Purch — Streamlit → Reflex Migration Notes

Structural companion doc. The full analysis lives in this file — moved
here from `app/MIGRATION.md` as part of the project-structure
normalization pass.

## Normalized layout (current)

```
rxconfig.py                Points Reflex at the `purch` package
assets/
  purch_theme.css          Palette + chat-bubble / card / chip primitives
  purch_animations.css     Small keyframes (fade-in, rise)
purch/                     THE Reflex application package
  __init__.py
  purch.py                 The sole rx.App instance + add_page calls
  theme.py                 COLORS / CLASSES / ROUTES
  state.py                 Flat re-exports of every state class
  states/
    nav_state.py           Sidebar open/closed
    auth_state.py          Google OAuth placeholder + session shape
    chat_state.py          Chat message list, composer, local reply stub
  components/
    brand.py               Purch wordmark + Beta pill
    header.py              Fixed top nav
    layout.py              page_shell(...) — every page renders through this
    chat_bubble.py         User/assistant bubbles + typing indicator
  pages/
    index.py               Landing / hero (public)
    login.py               Two-panel branded sign-in
    chat.py                Stateful chat shell (local stub replies)
    analytics.py           Placeholder KPIs + "coming soon" card
agent/, llm/, db/          Framework-agnostic business logic (SHARED
                           between the Streamlit fallback and the
                           Reflex shell — imported directly by both)
app.py, ui/                Streamlit fallback (kept intact)
```

## Shared backend logic (single copy, two consumers)

The Streamlit fallback (`app.py` at repo root) imports from `agent/`,
`llm/`, and `db/` directly and must keep working during the migration.
Rather than duplicate that code, the Reflex shell imports the exact
same top-level packages — one implementation on disk, two consumers:

```python
from agent.graph import run_agent   # used by both app.py and purch/*
from db.models import insert_transaction
from llm.extraction import CATEGORIES
```

When phase 3 wires the real chat loop, `purch.states.chat_state.ChatState`
will call:

- `agent.graph.run_agent(user_id, message)` — the whole graph in one
  call, exactly as `app.py` already does.
- `db.models.*` — insert/query/update transactions, budgets, log.
- `llm.extraction.CATEGORIES` — canonical category list.
- `llm.tone.VALID_TONES` — canonical tone list.
- `db.connection.init_db` / `ensure_user` — startup + per-login.

No changes to any of these files were made during normalization.

## Deployment refactor needs

Streamlit and Reflex differ meaningfully at deploy time:

| Concern              | Streamlit today                              | Reflex target                                            |
|----------------------|----------------------------------------------|----------------------------------------------------------|
| Process model        | Single Python process, thread-per-session    | Frontend (Next.js build) + backend (FastAPI/WebSocket)   |
| Static assets        | Served inline                                | Compiled `assets/` served by the frontend                |
| Env vars             | `.env` via `python-dotenv`                   | Same, but must be present at **both** build and run time |
| Google OAuth         | `streamlit[auth]` + `st.login()`             | Custom — see §OAuth                                      |
| State persistence    | `st.session_state` (in-memory, per session)  | `rx.State` subclasses (backend, per client)              |
| DB filesystem access | Local `data/budget.db`                       | Local FS only works on single-node hosts                 |

## SQLite → Postgres / Supabase / Neon

`db/connection.py` and `db/models.py` currently talk to SQLite via the
stdlib `sqlite3` module. Fine for the Streamlit single-node deployment;
blocks any horizontally-scaled Reflex deployment.

- **Schema-level:** `db/schema.sql` ports cleanly to Postgres with three
  edits: `AUTOINCREMENT` → `GENERATED ALWAYS AS IDENTITY`,
  `datetime('now')` → `now()`, timestamps become `TIMESTAMPTZ` (which
  removes the `PH_OFFSET` hack in `to_local_time_str`).
- **Query-level:** models use `?` positional placeholders (SQLite
  style). Under Postgres these become `$1, $2, …` or `%s`. Best path is
  to introduce SQLAlchemy Core and let it emit the right dialect.
- **Supabase:** works via its Postgres endpoint; auth can be delegated
  to Supabase Auth (which also gives us Google OAuth). Requires
  row-level security policies keyed on `auth.uid()` matching
  `transactions.user_id`.
- **Neon:** drop-in Postgres.

Recommendation: introduce a `db/engine.py` that returns either
the current SQLite connection or a Postgres SQLAlchemy engine based on
`DATABASE_URL`, and keep the `db/models.py` function signatures
identical so `agent/nodes.py` never notices the change.

## OAuth options

Streamlit's `st.login()` handles OAuth inside the framework. Reflex has
no equivalent — options:

1. **`reflex-google-auth` / Authlib** — implement a
   `/auth/google/callback` route in Reflex; store the user's email in
   `AuthState`; mint a signed session cookie. Most work; keeps
   everything in-process.
2. **Supabase Auth** — if we migrate the DB to Supabase, delegate
   OAuth entirely; hydrate `AuthState` from Supabase's JWT. Fastest
   path; ties us to Supabase.
3. **Clerk / Auth0** — hosted, drop-in, framework-agnostic. Overkill
   for a single-provider (Google-only) flow but cleanest UX.

The `/login` page's "Continue with Google" button already routes
through `AuthState.begin_google_login`, which currently surfaces a
friendly "not yet available" message — swap the body of that handler
when the provider is chosen.

## Remaining phases

- **Phase 3 — Agent integration.** Call `backend.agent.graph.run_agent`
  from `ChatState.send_message`; render assistant replies as bubbles;
  propagate `pending_edit` / `pending_conversion` state; port the
  budget-alert banner logic.
- **Phase 4 — Sidebar / budgets / settings.** Total budget card,
  per-category progress bars, tone picker, log-out. Rebuild
  `ui/gauges.py` as `rx.el.svg` components.
- **Phase 4 — Analytics.** Trend, category breakdown, month-over-month
  cards using existing `db.models` helpers.
- **DB migration.** SQLAlchemy + `DATABASE_URL` env switch.
- **Timezone cleanup.** Drop the `PH_OFFSET` hack once timestamps are
  `TIMESTAMPTZ`.
- **Chat streaming.** Yield partial updates during LLM latency.
- **Retire Streamlit shell.** Once parity is reached, move `app.py` /
  `ui/` to `archive/`.
