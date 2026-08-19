# Purch

Purch is a chat-based budget tracker built with **Reflex**. Users can record purchases conversationally, review wallets and analytics, and authenticate through Supabase-backed flows. The repository now contains one Reflex application package and one deployment path.

## Architecture

The canonical Reflex application lives under `purch/`. Reflex discovers the application through `rxconfig.py`, which sets `app_name="purch"`; the sole `rx.App` instance and page registrations are in `purch/purch.py`.

| Directory or file | Responsibility |
|---|---|
| `purch/` | Reflex pages, components, state classes, application entry point, authentication, wallet logic, and Postgres-aware backend adapters |
| `agent/` | Framework-independent conversation graph and agent nodes |
| `llm/` | Extraction, intent, tone, safety, and Groq client helpers |
| `db/` | Shared data-model and connection helpers retained for compatibility and local development |
| `assets/` | Reflex CSS and static visual assets |
| `tests/` | Automated tests for the agent, database, extraction, intent, safety, tone, and UI smoke behavior |
| `reflex.lock/` | Reflex-generated frontend package and lock artifacts |
| `wireframe.json` | Product design reference |

The former Streamlit fallback and the superseded Reflex packages have been removed. New code should import from `purch.*`, `agent.*`, `llm.*`, or `db.*`; it should not recreate parallel application trees.

## Requirements

Use Python 3.11 or newer and install the dependencies from the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the application locally with:

```bash
reflex run
```

The Reflex frontend and backend are developed together locally. The active application name is `purch`, so the repository should be run from its root directory.

## Environment variables

The application reads secrets and service configuration from the environment. Do not commit a `.env` file or credentials.

| Variable | Purpose |
|---|---|
| `SUPABASE_URL` | Supabase project URL used by the authentication client |
| `SUPABASE_KEY` | Server-side Supabase key used by the authentication integration |
| `REFLEX_DB_URL` or `DB_URL` | PostgreSQL connection URL used by the Purch database backend |
| `GROQ_API_KEY` | Groq credential used by the LLM helpers |
| `PURCH_OAUTH_REDIRECT_URL` | Optional OAuth callback base URL |
| `API_URL` | Public Reflex backend URL used when exporting or serving the frontend separately |

For local development, load these values through the shell or an untracked `.env` file supported by the existing Python helpers. For deployment, configure them through the hosting provider's secret/environment-variable settings.

## Supabase and PostgreSQL

The active Purch backend includes a SQLAlchemy/PostgreSQL path in `purch/db_backend.py` and a Supabase authentication wrapper in `purch/supabase_auth.py`. The code looks for `REFLEX_DB_URL` first and then `DB_URL` for the database connection. It looks for `SUPABASE_URL` and `SUPABASE_KEY` for Supabase authentication.

The repository does not contain the private Supabase project URL or credentials. Those values belong in deployment secrets. The relevant source files are [`purch/db_backend.py`](purch/db_backend.py), [`purch/supabase_auth.py`](purch/supabase_auth.py), and [`purch/states/auth_state.py`](purch/states/auth_state.py).

## Testing and validation

Run the test suite from the repository root:

```bash
pytest -q
```

For a dependency-independent syntax check:

```bash
python -m compileall -q agent db llm purch tests rxconfig.py
```

## Vercel deployment position

Reflex's export workflow produces a compiled frontend and a separate backend artifact. The frontend can be deployed to Vercel, but the Reflex backend must remain reachable at a public URL. The initial recommended production topology is therefore:

```text
Browser → Vercel-hosted Reflex frontend → separate Reflex backend/WebSocket service → Supabase PostgreSQL
```

Export the frontend with the backend URL available at build time:

```bash
API_URL=https://backend.example.com reflex export --frontend-only
```

Deploy the generated frontend to Vercel. Deploy the Reflex backend to a service that supports the required Python process and long-lived event/WebSocket behavior, then configure the Vercel project with the corresponding public backend URL. A single-provider Vercel backend deployment may be investigated separately using Vercel's Python and WebSocket capabilities, but it is not assumed to be compatible with the complete Reflex backend until tested.

Before production, verify Supabase Row Level Security, OAuth redirect URLs, database connection pooling, backend CORS/origin settings, frontend build-time environment variables, and the behavior of all Reflex event WebSockets. Local SQLite behavior should not be treated as the production persistence model when the Supabase PostgreSQL path is available.

## Project planning

Feature and migration notes are maintained in [`plan.md`](plan.md) and [`purch/MIGRATION.md`](purch/MIGRATION.md). The migration document records the remaining work separately from this structural cleanup, including deployment hardening, authentication completion, and any direct Vercel backend compatibility experiment.
