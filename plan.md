## Purch Streamlit-to-Reflex Migration Plan
- [ ] Analyze the existing Purch architecture and create the new Reflex shell with routing, global espresso/coral styling, and preserved Streamlit fallback files untouched.
- [ ] Rebuild the Purch login and chat-first experience in Reflex with responsive branded UI, stateful conversation flow, clear empty/loading/error states, and Google OAuth migration points prepared.
- [ ] Connect the existing LangGraph agent, LLM extraction, database, transaction creation, budget tracking, and pending edit/conversion flows into Reflex state without removing the current backend logic.
- [ ] Rebuild the sidebar, budget dashboard, analytics, and settings surfaces in Reflex, including deployment notes for SQLite limitations and PostgreSQL/Supabase/Neon compatibility plus remaining migration issues.
