## Deployment Websocket Stability Plan
- [x] Harden chat event execution for deployment: preserve the Purch espresso/coral parchment design direction while ensuring Groq rate limits and backend exceptions always resolve the event cleanly with user-safe feedback.
- [x] Reduce Groq token pressure in phase 3 agent calls by trimming prompts/model settings and adding lightweight retry/backoff for transient 429 errors so a single rate spike does not break the live websocket session.
- [x] Verify the fixed chat and backend error paths with focused event tests that do not mutate Supabase data.