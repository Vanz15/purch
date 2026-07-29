## Login And Stability Plan
- [x] Authentication experience: preserve the Purch espresso/coral parchment design direction while replacing the placeholder login with Google OAuth via Supabase, email/password account creation and sign-in, guest sign-in with a generated unique ID, clear session status, and updated login UI.
- [x] Identity enforcement: remove shared anonymous access for app data, route chat/sidebar/analytics through the active Google/email/guest identity, persist guest identity locally, and show safe prompts when no account is active.
- [x] Refresh and timeout stability: reduce DB refresh latency, cache sidebar/analytics data during refreshes, use async/pooled read paths where possible, avoid duplicate mount refreshes, and ensure timeout failures resolve with safe UI messages instead of websocket errors.
- [x] in analytics, allow to change month of analytics shown. only show in dropdown menu available months
- [x] while i am using the app on phone, connection timeout in laptop when simultaneously use. handle multiple sessions in one user account
- [x] update time to use ph time by default, or where user is
- [x] add free backup model for conversation and thinking model each from the same router, when either is not working due to request timeout or limits. example, if gpt-oss-120b is not working, use gpt-oss-20b.