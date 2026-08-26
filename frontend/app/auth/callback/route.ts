import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

// Handles the Google OAuth redirect: exchange the code for a session, then
// send the user to the chat. The PKCE verifier lives in an httpOnly cookie
// managed by @supabase/ssr — no Python server process involved, so the
// cross-worker verifier bug from the old Reflex OAuth flow cannot occur.
export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const next = searchParams.get("next") ?? "/chat";

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      return NextResponse.redirect(`${origin}${next}`);
    }
  }

  // Exchange failed (or no code) — bounce back to login with an error flag.
  return NextResponse.redirect(`${origin}/login?error=auth`);
}
