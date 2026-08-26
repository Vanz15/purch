"""Local smoke test: mint a valid HS256 Supabase-style JWT from the configured
JWT secret, then hit the real FastAPI routes with it. Verifies the auth
dependency + live DB path without needing a browser. Run: python smoke.py
"""
import json
import os
import time
import urllib.request

from dotenv import load_dotenv

load_dotenv()

SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")
BASE = "http://127.0.0.1:8011"
# Use the email identity confirmed in Phase 2 (sample row from transactions)
TEST_EMAIL = os.getenv("TEST_USER_EMAIL", "aivannpmartinez@gmail.com")


def make_token(secret: str, email: str) -> str:
    # Minimal HS256 JWT compatible with python-jose decode (alg HS256, aud 'authenticated')
    import hmac
    import hashlib
    import base64

    def b64(b: bytes) -> str:
        return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

    header = b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = b64(json.dumps({
        "sub": "test-sub",
        "email": email,
        "aud": "authenticated",
        "role": "authenticated",
        "exp": int(time.time()) + 3600,
    }).encode())
    signing_input = f"{header}.{payload}".encode()
    sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    return f"{header}.{payload}.{b64(sig)}"


def req(method: str, path: str, token: str, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Authorization", f"Bearer {token}")
    r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


if __name__ == "__main__":
    if not SECRET:
        print("SKIP: SUPABASE_JWT_SECRET not set")
        raise SystemExit
    tok = make_token(SECRET, TEST_EMAIL)
    print("== GET /api/wallets ==")
    print(req("GET", "/api/wallets", tok))
    print("== GET /api/wallets/summary ==")
    print(req("GET", "/api/wallets/summary", tok))
    print("== GET /api/tone ==")
    print(req("GET", "/api/tone", tok))
    print("== POST /api/chat (lent message) ==")
    print(req("POST", "/api/chat", tok, {"message": "lent 300 to Maria"}))
    print("== POST /api/chat (wallet question) ==")
    print(req("POST", "/api/chat", tok, {"message": "how much is left?"}))
    print("== POST /api/chat (no wallet yet -> should park) ==")
    print(req("POST", "/api/chat", tok, {"message": "coffee 150 cash"}))
