"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { ArrowRight } from "lucide-react";

const REFERRAL_OPTIONS = [
  "Instagram",
  "Facebook",
  "LinkedIn",
  "Friend",
  "Others",
];

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [referral, setReferral] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    // Validate email has @
    if (!email.includes("@")) {
      setError("Please enter a valid email address.");
      return;
    }

    // Password min length
    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }

    // Username not empty
    if (!username.trim()) {
      setError("Username is required.");
      return;
    }

    setLoading(true);

    try {
      const supabase = createClient();

      // Check if username is unique
      const { data: existing } = await supabase
        .from("users")
        .select("id")
        .eq("username", username.trim())
        .limit(1);

      if (existing && existing.length > 0) {
        setError("Username is already taken.");
        setLoading(false);
        return;
      }

      // Sign up with Supabase Auth
      const { data, error: authError } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            full_name: username.trim(),
            username: username.trim(),
            referral: referral || null,
          },
        },
      });

      if (authError) {
        setError(authError.message);
        setLoading(false);
        return;
      }

      if (data.user) {
        // Insert username into users table
        await supabase.from("users").upsert({
          id: data.user.id,
          email: email,
          username: username.trim(),
          referral: referral || null,
        });

        router.push("/chat");
      }
    } catch (err) {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleGoogleRegister() {
    const supabase = createClient();
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    });
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#F5F5F7] px-4">
      <div className="w-full max-w-[400px]">
        {/* Logo */}
        <div className="text-center mb-8">
          <Link href="/" className="inline-block">
            <span
              style={{
                fontFamily: "'Playfair Display', Georgia, serif",
                fontWeight: 600,
                fontStyle: "italic",
                fontSize: 28,
                color: "#171717",
                letterSpacing: "-0.02em",
              }}
            >
              purch
            </span>
          </Link>
        </div>

        {/* Register card */}
        <div
          className="rounded-2xl p-8"
          style={{
            background: "#fff",
            boxShadow:
              "rgba(0,0,0,0.06) 0px 1px 3px 0px, rgba(0,0,0,0.06) 0px 8px 16px 0px",
          }}
        >
          <h1
            className="text-center mb-1"
            style={{
              fontSize: 22,
              fontWeight: 600,
              color: "#181925",
              letterSpacing: "-0.02em",
            }}
          >
            Create your account
          </h1>
          <p
            className="text-center mb-6"
            style={{ fontSize: 14, color: "#999" }}
          >
            Start tracking your spending with Purch.
          </p>

          {error && (
            <div
              className="mb-4 px-3 py-2 rounded-lg text-sm"
              style={{ background: "#fef2f2", color: "#dc2626" }}
            >
              {error}
            </div>
          )}

          <form onSubmit={handleRegister} className="flex flex-col gap-3.5">
            <div>
              <label
                className="block mb-1.5"
                style={{
                  fontSize: 13,
                  fontWeight: 500,
                  color: "#666",
                }}
              >
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full rounded-lg px-3.5 py-2.5 text-sm bg-white outline-none transition-colors"
                style={{
                  border: "1px solid #e8e8e8",
                  color: "#181925",
                }}
                onFocus={(e) =>
                  (e.currentTarget.style.borderColor = "#7c6edc")
                }
                onBlur={(e) =>
                  (e.currentTarget.style.borderColor = "#e8e8e8")
                }
              />
            </div>

            <div>
              <label
                className="block mb-1.5"
                style={{
                  fontSize: 13,
                  fontWeight: 500,
                  color: "#666",
                }}
              >
                Username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="yourusername"
                className="w-full rounded-lg px-3.5 py-2.5 text-sm bg-white outline-none transition-colors"
                style={{
                  border: "1px solid #e8e8e8",
                  color: "#181925",
                }}
                onFocus={(e) =>
                  (e.currentTarget.style.borderColor = "#7c6edc")
                }
                onBlur={(e) =>
                  (e.currentTarget.style.borderColor = "#e8e8e8")
                }
              />
            </div>

            <div>
              <label
                className="block mb-1.5"
                style={{
                  fontSize: 13,
                  fontWeight: 500,
                  color: "#666",
                }}
              >
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Min. 6 characters"
                className="w-full rounded-lg px-3.5 py-2.5 text-sm bg-white outline-none transition-colors"
                style={{
                  border: "1px solid #e8e8e8",
                  color: "#181925",
                }}
                onFocus={(e) =>
                  (e.currentTarget.style.borderColor = "#7c6edc")
                }
                onBlur={(e) =>
                  (e.currentTarget.style.borderColor = "#e8e8e8")
                }
              />
            </div>

            <div>
              <label
                className="block mb-1.5"
                style={{
                  fontSize: 13,
                  fontWeight: 500,
                  color: "#666",
                }}
              >
                How did you hear about Purch?
              </label>
              <select
                value={referral}
                onChange={(e) => setReferral(e.target.value)}
                className="w-full rounded-lg px-3.5 py-2.5 text-sm bg-white outline-none transition-colors"
                style={{
                  border: "1px solid #e8e8e8",
                  color: referral ? "#181925" : "#999",
                  appearance: "auto",
                }}
                onFocus={(e) =>
                  (e.currentTarget.style.borderColor = "#7c6edc")
                }
                onBlur={(e) =>
                  (e.currentTarget.style.borderColor = "#e8e8e8")
                }
              >
                <option value="" disabled>
                  Select an option
                </option>
                {REFERRAL_OPTIONS.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 mt-2 rounded-full py-2.5 text-sm font-semibold transition-opacity"
              style={{
                background: "#7C6EDC",
                color: "#fff",
                cursor: loading ? "not-allowed" : "pointer",
                opacity: loading ? 0.7 : 1,
              }}
            >
              {loading ? "Creating account…" : "Register"}
              {!loading && <ArrowRight size={15} />}
            </button>
          </form>

          {/* Divider */}
          <div className="flex items-center gap-3 my-5">
            <div className="flex-1 h-px" style={{ background: "#e8e8e8" }} />
            <span style={{ fontSize: 12, color: "#999" }}>or</span>
            <div className="flex-1 h-px" style={{ background: "#e8e8e8" }} />
          </div>

          {/* Google */}
          <button
            onClick={handleGoogleRegister}
            className="w-full flex items-center justify-center gap-2.5 rounded-full py-2.5 text-sm font-medium transition-opacity hover:opacity-90"
            style={{
              background: "#fff",
              color: "#181925",
              border: "1px solid #e8e8e8",
              cursor: "pointer",
            }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24">
              <path
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
                fill="#4285F4"
              />
              <path
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                fill="#34A853"
              />
              <path
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                fill="#FBBC05"
              />
              <path
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                fill="#EA4335"
              />
            </svg>
            Continue with Google
          </button>

          {/* Footer */}
          <p
            className="text-center mt-5"
            style={{ fontSize: 13, color: "#999" }}
          >
            Already have an account?{" "}
            <Link
              href="/auth/login"
              style={{ color: "#7c6edc", fontWeight: 500, textDecoration: "none" }}
            >
              Log in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
