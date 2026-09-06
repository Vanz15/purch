"use client";

// Guest identity + token manager.
//
// When the user picks "Continue as guest", we generate a stable guest id
// (stored in localStorage) and exchange it for a short-lived JWT from the
// backend's /api/guest-token endpoint. The token is minted with the same
// SUPABASE_JWT_SECRET the backend uses for real Supabase sessions, so the
// API accepts it identically. The token is cached in memory for the session.

const LS_GUEST_ID = "purch_guest_id";

function guestId(): string {
  let id = localStorage.getItem(LS_GUEST_ID);
  if (!id) {
    id = `guest-${crypto.randomUUID().replace(/-/g, "")}`;
    localStorage.setItem(LS_GUEST_ID, id);
  }
  return id;
}

let cachedToken: string | null = null;

export function isGuest(): boolean {
  return !!localStorage.getItem(LS_GUEST_ID);
}

export function guestName(): string {
  const id = localStorage.getItem(LS_GUEST_ID) || "";
  // e.g. "Guest040d"
  return `Guest${id.replace("guest-", "").slice(0, 4)}`;
}

export function guestDetail(): string {
  const id = localStorage.getItem(LS_GUEST_ID) || "";
  // e.g. "Guest040dea"
  return `Guest${id.replace("guest-", "").slice(0, 7)}`;
}

export function ensureGuest(): string {
  return guestId();
}

export async function getGuestToken(): Promise<string | null> {
  if (cachedToken) return cachedToken;
  const id = guestId();
  // Dynamic API URL
  let API_URL = "";
  if (typeof window !== "undefined") {
    const envUrl = process.env.NEXT_PUBLIC_API_URL;
    if (envUrl && window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1") {
      API_URL = envUrl;
    } else {
      API_URL = window.location.origin.replace(":3000", ":8000");
    }
  }
  try {
    const res = await fetch(`${API_URL}/api/guest-token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ guest_id: id }),
    });
    if (!res.ok) return null;
    const data = await res.json();
    cachedToken = data.access_token;
    return cachedToken;
  } catch {
    return null;
  }
}

export function clearGuest() {
  localStorage.removeItem(LS_GUEST_ID);
  cachedToken = null;
}
