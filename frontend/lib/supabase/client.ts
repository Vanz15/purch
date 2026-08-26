import { createBrowserClient } from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";

// Memoize a single browser client so its auth session persists across calls.
// Creating a fresh client per request means the session hasn't rehydrated
// yet, so getSession() returns null and no Authorization header is sent
// (causing "Missing bearer token" 401s on Vercel).
let _client: SupabaseClient | null = null;

export function createClient(): SupabaseClient {
  if (!_client) {
    _client = createBrowserClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    );
  }
  return _client;
}
