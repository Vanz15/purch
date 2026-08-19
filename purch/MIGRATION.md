# Purch Migration and Deployment Notes

## Current canonical architecture

The repository is now organized around one Reflex application package:

```text
rxconfig.py
assets/
purch/
  purch.py                 sole rx.App instance and page registration
  theme.py                 visual tokens and routes
  state.py                 convenience state re-exports
  states/                  Reflex state classes
  components/              shared UI components
  pages/                   route-level page components
  db_backend.py            SQLAlchemy/PostgreSQL adapter
  supabase_auth.py         Supabase authentication wrapper
  wallet_backend.py        wallet persistence and queries
  wallet_intent.py         wallet intent parsing
  wallet_llm.py            wallet-related LLM helpers
agent/                     framework-independent agent graph
llm/                       extraction, intent, tone, safety, Groq helpers
db/                        shared database models and local compatibility path
tests/                     automated test suite
```

`rxconfig.py` sets `app_name="purch"`, and `purch/purch.py` is the only module that creates `rx.App` or registers pages. The legacy `app/` and `app.app/` Reflex trees, the root Streamlit entry point, and the `ui/` Streamlit components are no longer part of the project.

## Shared business logic

The canonical Reflex shell imports shared framework-independent code directly from `agent/`, `llm/`, and `db/`. There should be only one implementation of the conversation graph, extraction helpers, intent classification, safety checks, and core data-model operations. New Reflex code belongs under `purch/` and should not create another application package or duplicate page/state/component trees.

## Supabase and PostgreSQL integration

The project already contains a PostgreSQL path intended for the Supabase database:

- `purch/db_backend.py` uses SQLAlchemy and reads `REFLEX_DB_URL` first, then `DB_URL`.
- `purch/supabase_auth.py` uses `SUPABASE_URL` and `SUPABASE_KEY` to create the Supabase client.
- `purch/backend.py` selects the PostgreSQL adapter when a supported database URL is present.
- `purch/states/analytics_state.py` and `purch/wallet_backend.py` use the backend selection to access PostgreSQL-aware operations.

The repository intentionally does not contain a private Supabase project URL, database password, or API key. Configure those values as deployment secrets. The public repository links to the relevant implementation files: [`purch/db_backend.py`](https://github.com/Vanz15/chat-based-budget-tracker/blob/cleanup/reflex-only-vercel-ready/purch/db_backend.py), [`purch/supabase_auth.py`](https://github.com/Vanz15/chat-based-budget-tracker/blob/cleanup/reflex-only-vercel-ready/purch/supabase_auth.py), and [`purch/states/auth_state.py`](https://github.com/Vanz15/chat-based-budget-tracker/blob/cleanup/reflex-only-vercel-ready/purch/states/auth_state.py).

The local SQLite path remains useful as a compatibility and development fallback, but production should use the Supabase/PostgreSQL path. Database initialization and schema changes should be managed deliberately rather than running destructive DDL during application startup.

## Vercel deployment position

Reflex produces a frontend and a backend with different runtime responsibilities. The official Reflex documentation explains that the compiled frontend can be deployed to a static host such as Vercel, while the backend must be deployed separately. The initial production topology is therefore:

```text
Vercel static frontend
        │
        │ API_URL / event WebSocket URL
        ▼
Separate Reflex backend service
        │
        ├── Supabase authentication
        ├── Groq/LLM services
        └── Supabase PostgreSQL
```

The relevant official documentation is [Reflex CLI export](https://reflex.dev/docs/api-reference/cli/), [Reflex self-hosting](https://reflex.dev/docs/hosting/self-hosting/), [Vercel Python Functions](https://vercel.com/docs/functions/runtimes/python), and [Vercel WebSockets](https://vercel.com/docs/functions/websockets). Vercel's Python and WebSocket capabilities make a direct backend experiment possible, but Reflex-specific compatibility is not assumed. The default plan is to deploy the static frontend on Vercel and use a long-running, WebSocket-capable service for the Reflex backend.

Export the frontend with the public backend URL available at build time:

```bash
API_URL=https://backend.example.com reflex export --frontend-only
```

The backend must expose its event/WebSocket endpoints at the URL baked into the export. If a reverse proxy places the backend under a subpath, configure Reflex's `backend_path` rather than relying on ad hoc request rewriting. The Vercel project should receive only public frontend configuration and non-secret build settings; database, Supabase, Groq, and backend secrets belong to the backend service.

## Deployment hardening checklist

Before production deployment, verify that the backend has a stable public URL, the Vercel frontend uses the correct `API_URL`, Supabase OAuth redirect URLs include the deployed login callback, Supabase Row Level Security protects records by user identity, and the backend service supports Reflex's event WebSockets. Configure PostgreSQL connection pooling and avoid depending on ephemeral local filesystem state.

The project should also be checked for frontend build-time asset resolution, correct CORS and origin behavior, timezone handling, error logging, and secret redaction. A Vercel preview deployment should be tested against a non-production backend or controlled Supabase environment before promoting it.

## Remaining application work

Structural cleanup is separate from feature completion. The remaining work should be tracked and implemented independently:

1. Complete the real agent integration in `ChatState` and verify transaction persistence through the PostgreSQL adapter.
2. Complete authentication and OAuth callback behavior using the existing Supabase integration.
3. Harden wallet, analytics, and budget flows against the Supabase schema and Row Level Security policies.
4. Validate Reflex frontend export and deploy the frontend to Vercel.
5. Deploy and observe the Reflex backend on a WebSocket-capable service.
6. Optionally run a separate compatibility experiment for hosting the Reflex backend in Vercel Python/WebSocket Functions.

Do not reintroduce Streamlit files or create another top-level Reflex package while completing these phases.
