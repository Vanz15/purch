# Purch — Streamlit → Reflex Migration Analysis

Companion doc to `plan.md`. This is the phase-1 deliverable: an honest
inventory of what exists today, what carries over cleanly, and what
still has to be rebuilt or replaced before Purch can ship on Reflex.

The Streamlit implementation is **not** being deleted. Both shells will
coexist on disk until the Reflex shell reaches feature parity, at which
point the Streamlit files become the fallback / reference implementation.

---

## 1. Current architecture (Streamlit)

```
app.py                     Streamlit entry — auth gate, chat UI, sidebar
ui/styles.py               ~700 lines of injected CSS (espresso/coral theme)
ui/gauges.py               SVG budget gauges (semi-circular + horizontal bar)
agent/
  graph.py                 LangGraph state machine wiring
  nodes.py                 try_extract → finalize / classify / query / edit / budget
  state.py                 AgentState TypedDict
llm/
  groq_client.py           Singleton Groq client + THINKING/CONVERSATION model IDs
  extraction.py            Purchase extraction (tool-calling)
  intent.py                Intent classification
  query_extraction.py      NL query → SQL filters
  budget_extraction.py     "set food budget to 3000" parsing
  edit_extraction.py       Edit/delete intent parsing
  tone.py                  6 personality tones + Taglish/Kapampangan personas
  safety.py                Prompt-injection heuristic
db/
  connection.py            SQLite connection + init_db + ensure_user
  models.py                Transactions / budgets / interaction log CRUD
  schema.sql               users / transactions / budgets / interaction_log
tests/                     pytest suite (extraction, agent, budgets, edit, safety)
```

Runtime: Streamlit + `streamlit[auth]` (Google OAuth via `st.login()`).
Storage: SQLite file at `data/budget.db`.
LLM: Groq (`openai/gpt-oss-20b` for tool calls, `llama-3.3-70b-versatile`
for conversational tone rewrites).

---

## 2. Streamlit-specific files (do not import from Reflex)

These lean on Streamlit primitives and can't be reused as-is:

- `app.py` — uses `st.session_state`, `st.chat_input`, `st.sidebar`,
  `st.user`, `st.login()`, `st.container(key=…)`, `st.columns`,
  `st.rerun()`.
- `ui/styles.py` — injects a massive CSS block via `st.html`. The
  **palette and design tokens** were lifted into `assets/purch_theme.css`
  and `app/theme.py` for the Reflex shell; layout-specific selectors
  (e.g. `.st-key-app_header`, `section[data-testid="stSidebar"]`) were
  left behind because they only match Streamlit's DOM.
- `ui/gauges.py` — pure SVG strings returned to `st.html`. Portable in
  spirit, but will be rebuilt as `rx.el.svg` components when the sidebar
  budget widget lands in the Reflex shell.

**Left untouched by design.** Neither file is imported anywhere under
`app/` in the Reflex shell.

---

## 3. Reusable backend logic (imported as-is from Reflex)

Everything under `agent/`, `llm/`, and `db/` is framework-agnostic
Python. The Reflex event handlers (phase 3) will call:

- `agent.graph.run_agent(user_id, message)` — the whole graph in one
  call, exactly as `app.py` already does.
- `db.models.*` — `insert_transaction`, `get_recent_transactions`,
  `get_budget`, `get_month_spent`, `get_all_budgets_and_spending`,
  `find_best_match_transaction`, `update_transaction`,
  `delete_transaction`, `set_user_tone`, `get_user_tone`.
- `llm.extraction.CATEGORIES` — canonical category list, needed by
  budget/settings surfaces.
- `llm.tone.VALID_TONES` — canonical tone list, needed by the tone
  picker.
- `db.connection.init_db` / `ensure_user` — call once on Reflex app
  startup and per-login respectively.

**No changes made to any of these files in phase 1.** The Reflex shell
imports nothing from them yet either — that wiring is phase 3.

---

## 4. New Reflex shell layout (this phase)

```
rxconfig.py                Points Reflex at the `app` package (unchanged)
assets/
  purch_theme.css          Global CSS: font imports, palette variables,
                           chat-bubble / card / chip primitives
app/
  __init__.py
  app.py                   rx.App + add_page for /, /login, /chat, /analytics
  theme.py                 COLORS + reusable CLASSES + ROUTES table
  states/
    nav_state.py           NavState (sidebar_open toggle, placeholder)
  components/
    brand.py               Purch wordmark + Beta pill
    header.py              Fixed top bar with nav links
    layout.py              page_shell(...) — every page renders through this
  pages/
    index.py               Landing / hero (public)
    login.py               Placeholder login (OAuth wired later)
    chat.py                Chat shell + empty state + disabled composer
    analytics.py           Placeholder KPIs + "coming soon" card
```

Design decisions worth flagging:

- **CSS-first theming.** Palette lives in `assets/purch_theme.css` as
  CSS custom properties (`--purch-coral`, `--purch-parchment`, etc.) and
  is mirrored in `app/theme.py::COLORS`. Components reference the CSS
  vars via Tailwind arbitrary values (`bg-[color:var(--purch-coral)]`)
  so a palette change is a one-file edit.
- **Routes, not screens.** The Streamlit app switched screens via
  `st.session_state.screen`; the Reflex shell uses real routes
  (`/`, `/login`, `/chat`, `/analytics`) exposed via `app.add_page`.
  The route table lives in `app/theme.py::ROUTES` so header links and
  `add_page` calls stay in sync.
- **Shared page shell.** `page_shell(...)` in `components/layout.py`
  renders the fixed header + parchment background + content column so
  each page is just its own content.

---

## 5. Deployment refactor needs

Streamlit and Reflex differ meaningfully at deploy time:

| Concern              | Streamlit today                              | Reflex target                                            |
|----------------------|----------------------------------------------|----------------------------------------------------------|
| Process model        | Single Python process, thread-per-session    | Frontend (Next.js build) + backend (FastAPI/WebSocket)   |
| Static assets        | Served inline                                | Compiled `assets/` directory served by the frontend      |
| Env vars             | `.env` via `python-dotenv`                   | Same, but must be present at **both** build and run time |
| Google OAuth         | `streamlit[auth]` + `st.login()`             | Custom — see §7                                          |
| State persistence    | `st.session_state` (in-memory, per session)  | `rx.State` subclasses (backend, per client)              |
| DB filesystem access | Local `data/budget.db`                       | Local FS only works on single-node hosts — see §6        |

The Reflex shell itself has no runtime dependencies on Streamlit, so the
two can be deployed independently while the migration is ongoing.

---

## 6. SQLite limitations & Postgres / Supabase / Neon compatibility

`db/connection.py` and `db/models.py` currently talk to SQLite via the
stdlib `sqlite3` module. This works fine for the Streamlit single-node
deployment but blocks any horizontally-scaled Reflex deployment:

- **Single-writer, file-locked.** Concurrent Reflex backend workers on
  the same host will contend; workers on different hosts can't share
  the file at all.
- **Ephemeral filesystems.** Reflex Cloud / Fly / Render / Railway all
  wipe local disk on redeploy — the SQLite file would vanish.
- **No connection pooling.** Every `get_connection()` opens/closes a
  fresh connection. Fine on SQLite; wasteful on Postgres.

**Compatibility notes for the migration:**

- **Schema-level:** `db/schema.sql` uses only `TEXT`, `INTEGER`, `REAL`,
  `AUTOINCREMENT`, `datetime('now')`, and a single `ON CONFLICT … DO
  UPDATE` clause. All of that ports cleanly to Postgres with three
  edits: `AUTOINCREMENT` → `GENERATED ALWAYS AS IDENTITY` (or `SERIAL`),
  `datetime('now')` → `now()`, and stored timestamps become `TIMESTAMPTZ`
  (which removes the `PH_OFFSET` hack in `to_local_time_str`).
- **Query-level:** the models module uses `?` positional placeholders
  (SQLite style). Under Postgres these become `$1, $2, …` or `%s` under
  psycopg. Best migration path is to introduce SQLAlchemy Core (or
  `databases` + SQLAlchemy) and let it emit the right dialect; the
  handful of raw queries are short enough to port in an afternoon.
- **Supabase:** works via its Postgres endpoint; auth can be delegated
  to Supabase Auth (which also gives us Google OAuth for free — see §7).
  Requires row-level security policies keyed on `auth.uid()` matching
  `transactions.user_id`.
- **Neon:** drop-in Postgres. Nothing Purch-specific to worry about
  beyond the schema/query changes above.
- **Transactions:** `insert_transaction` already wraps in a try/except
  with `conn.rollback()` — that pattern carries over unchanged.

Recommendation: introduce a `db/engine.py` that returns either the
current SQLite connection or a Postgres SQLAlchemy engine based on a
`DATABASE_URL` env var, and keep the `db/models.py` function signatures
identical so `agent/nodes.py` never notices the change.

---

## 7. Google OAuth migration considerations

Streamlit's `st.login()` handles the OAuth dance inside the framework
via `.streamlit/secrets.toml`. Reflex has no equivalent — options:

1. **Reflex-first (`reflex-google-auth` or `Authlib`)** — implement a
   `/auth/google/callback` route in Reflex that completes the OAuth
   code exchange, stores the user's email in an `AuthState`, and mints
   a signed session cookie. Most work; keeps everything in-process.
2. **Supabase Auth** — if we migrate the DB to Supabase (see §6), we
   can delegate OAuth entirely to Supabase and hydrate a Reflex
   `AuthState` from Supabase's JWT. Fastest path; ties us to Supabase.
3. **Clerk / Auth0** — hosted, drop-in, framework-agnostic. Overkill
   for a single-provider (Google-only) flow but cleanest UX.

In all three cases, the identifier that lands in
`db.models.ensure_user(user_id)` is still just an email string, so
nothing under `db/` or `agent/` has to change.

The Reflex shell's `/login` page is a **visual placeholder** for now —
the "Continue with Google" button is intentionally disabled so it's
obvious this is not wired yet.

---

## 8. Remaining issues for later phases

Rolling checklist, roughly in the order they should be tackled:

- [ ] **Phase 2 — Auth + chat UI.** Wire real Google OAuth (§7), build
      the `ChatState` (message list, pending edit/conversion, rate
      limit window), port the empty-state and chat-bubble treatments
      one-to-one.
- [ ] **Phase 3 — Agent integration.** Call `run_agent` from a Reflex
      event handler; render assistant replies as bubbles; propagate
      `pending_edit` / `pending_conversion` state; port the budget
      alert banner logic that currently lives inline in
      `finalize_add_transaction_node`.
- [ ] **Phase 4 — Sidebar / budgets / settings.** Rebuild the total
      budget card, per-category progress bars, tone picker, and log-out
      as Reflex components (probably behind a collapsible drawer that
      respects `NavState.sidebar_open`). Rebuild `ui/gauges.py` as
      `rx.el.svg` components.
- [ ] **Phase 4 — Analytics.** Trend, category breakdown, month-over-
      month cards. Backend queries already exist in `db.models`; we
      likely add one or two aggregate helpers.
- [ ] **DB migration.** Introduce SQLAlchemy + a `DATABASE_URL` env
      switch so we can point at Postgres (Supabase / Neon) without
      touching `agent/` or `llm/`.
- [ ] **Timezone cleanup.** Drop the `PH_OFFSET` hack in
      `db/models.to_local_time_str` once timestamps are stored as
      `TIMESTAMPTZ`; render locally in the UI instead.
- [ ] **Chat streaming.** The current agent returns one final string.
      Reflex supports yielding partial updates from an event handler —
      worth exploring once the base loop works.
- [ ] **Observability.** `interaction_log` is written to but never
      read. Add a lightweight admin view (or export to Supabase
      Studio) so we can spot-check extraction quality post-launch.
- [ ] **Retire Streamlit shell.** Once the Reflex shell reaches parity,
      move `app.py` / `ui/` into an `archive/` directory rather than
      deleting them — they're useful reference for a while.

---

## 9. What phase 1 explicitly did NOT do

To keep the diff reviewable and the fallback intact:

- No changes to `app.py`, `ui/styles.py`, `ui/gauges.py`.
- No changes to anything under `agent/`, `llm/`, `db/`, or `tests/`.
- No new runtime dependencies (Reflex is already available in the
  environment; `rxconfig.py` predates this phase).
- No OAuth, no chat loop, no live data — the Reflex pages are static
  shells rendered from the design tokens only.

Everything above is deferred to the phases listed in §8.
