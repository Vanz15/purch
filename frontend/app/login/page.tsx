"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

type Mode = "signin" | "signup" | "recover";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) router.replace("/chat");
    });
  }, [router]);

  async function signInWithGoogle() {
    setBusy(true);
    setError("");
    const supabase = createClient();
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${location.origin}/auth/callback` },
    });
    if (error) {
      setError(error.message);
      setBusy(false);
    }
    // On success the browser redirects to Google; nothing else to do here.
  }

  async function submitCredentials(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setInfo("");
    const supabase = createClient();
    try {
      if (mode === "signup") {
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
          options: { data: { name: name || undefined } },
        });
        if (error) throw error;
        if (!data.session) {
          setInfo("Check your inbox to confirm your email, then sign in.");
          setMode("signin");
        } else {
          router.replace("/chat");
        }
      } else if (mode === "recover") {
        const { error } = await supabase.auth.resetPasswordForEmail(email, {
          redirectTo: `${location.origin}/auth/callback`,
        });
        if (error) throw error;
        setInfo("If that email exists, a reset link is on its way.");
      } else {
        const { data, error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (error) throw error;
        if (data.session) router.replace("/chat");
      }
    } catch (err: any) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  function signInAsGuest() {
    // No Supabase user — identity stays local to this browser.
    const uuid = crypto.randomUUID().replace(/-/g, "").slice(0, 12);
    const guestEmail = `guest-${uuid}@purch.local`;
    localStorage.setItem("purch_user_email", guestEmail);
    localStorage.setItem("purch_user_name", `Guest ${uuid.slice(0, 6)}`);
    localStorage.setItem("purch_auth_method", "guest");
    router.replace("/chat");
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-[#faf6ef] px-4">
      <div className="w-full max-w-md bg-[#fffdf8] rounded-2xl shadow-sm border border-[#e7ddd0] p-8">
        <h1 className="text-3xl font-bold text-[#2b2118]">Purch</h1>
        <p className="text-sm text-[#8a7c6b] mt-1">
          Budget tracking, reimagined.
        </p>

        {info && (
          <div className="mt-4 p-3 rounded-xl border border-[#9fd0c4] bg-[#f1faf7] text-sm text-[#2b2118]">
            ✓ {info}
          </div>
        )}
        {error && (
          <div className="mt-4 p-3 rounded-xl border border-[#e36b5e] bg-[#fdecea] text-sm text-[#2b2118]">
            ⚠ {error}
          </div>
        )}

        <button
          onClick={signInWithGoogle}
          disabled={busy}
          className="mt-6 w-full rounded-xl bg-[#2b2118] text-white py-2.5 font-medium disabled:opacity-60"
        >
          {busy ? "Please wait…" : "Continue with Google"}
        </button>

        <div className="flex items-center gap-3 my-5">
          <div className="flex-1 h-px bg-[#e7ddd0]" />
          <span className="text-[0.65rem] uppercase tracking-[0.1em] text-[#8a7c6b]">
            or
          </span>
          <div className="flex-1 h-px bg-[#e7ddd0]" />
        </div>

        <form onSubmit={submitCredentials} className="flex flex-col gap-3">
          {mode === "signup" && (
            <input
              type="text"
              placeholder="Display name (optional)"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-xl border border-[#e7ddd0] bg-white px-3.5 py-2.5 text-sm"
            />
          )}
          <input
            type="email"
            required
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-xl border border-[#e7ddd0] bg-white px-3.5 py-2.5 text-sm"
          />
          {mode !== "recover" && (
            <input
              type="password"
              required
              placeholder="At least 6 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-xl border border-[#e7ddd0] bg-white px-3.5 py-2.5 text-sm"
            />
          )}
          {mode === "recover" ? (
            <button
              type="submit"
              disabled={busy}
              className="w-full rounded-xl bg-[#e36b5e] text-white py-2.5 font-medium disabled:opacity-60"
            >
              Send recovery link
            </button>
          ) : (
            <button
              type="submit"
              disabled={busy}
              className="w-full rounded-xl bg-[#e36b5e] text-white py-2.5 font-medium disabled:opacity-60"
            >
              {mode === "signup" ? "Create account" : "Sign in"}
            </button>
          )}
        </form>

        {mode === "signin" && (
          <button
            onClick={() => setMode("recover")}
            className="mt-2 text-xs text-[#8a7c6b] hover:text-[#e36b5e]"
          >
            Forgot password?
          </button>
        )}

        <button
          onClick={
            mode === "signup"
              ? () => setMode("signin")
              : () => setMode("signup")
          }
          className="mt-2 text-xs text-[#8a7c6b] hover:text-[#e36b5e]"
        >
          {mode === "signup"
            ? "Already have an account? Sign in"
            : "New to Purch? Create an account"}
        </button>

        <div className="mt-5 p-4 rounded-xl border border-dashed border-[#e7ddd0] bg-[#faf6ef]">
          <p className="text-xs text-[#8a7c6b] leading-relaxed">
            Prefer not to sign up? Start a private guest session — your chat
            stays on this device only.
          </p>
          <button
            onClick={signInAsGuest}
            className="mt-3 w-full rounded-xl border border-[#2b2118] text-[#2b2118] py-2 text-sm"
          >
            Continue as guest
          </button>
        </div>
      </div>
    </main>
  );
}
