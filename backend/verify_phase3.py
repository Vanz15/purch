"""Phase 3 verification WITHOUT a JWT secret.

The production auth dependency (app.deps.get_current_user_id) requires
SUPABASE_JWT_SECRET, which may not be handy right now. This harness
imports the real FastAPI app and overrides ONLY the auth dependency with a
fixed test user (the email identity confirmed in Phase 2) so we can prove
the route logic, DB wiring, and all 6 chat branches work against live data.

It does NOT modify app.deps — production behavior is untouched.
"""
import json
import os
import urllib.request
from dotenv import load_dotenv

load_dotenv()

BASE = "http://127.0.0.1:8012"
TEST_EMAIL = os.getenv("TEST_USER_EMAIL", "aivannpmartinez@gmail.com")

import app.main as m

# Override the auth dependency for this test only.
import app.deps as deps
from fastapi import Request

async def _test_user(request: Request) -> str:
    return TEST_EMAIL

m.app.dependency_overrides[deps.get_current_user_id] = _test_user

import uvicorn
import threading
import time

def _serve():
    uvicorn.run(m.app, host="127.0.0.1", port=8012, log_level="warning")

def req(method, path, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


if __name__ == "__main__":
    t = threading.Thread(target=_serve, daemon=True)
    t.start()
    time.sleep(4)
    print("== GET /api/wallets ==")
    print(req("GET", "/api/wallets"))
    print("== GET /api/wallets/summary ==")
    print(req("GET", "/api/wallets/summary"))
    print("== GET /api/tone ==")
    print(req("GET", "/api/tone"))
    print("== POST /api/chat (lent 300 to Maria) ==")
    print(req("POST", "/api/chat", {"message": "lent 300 to Maria"}))
    print("== POST /api/chat (wallet question) ==")
    print(req("POST", "/api/chat", {"message": "how much is left?"}))
    print("== POST /api/chat (purchase, no wallet named -> park) ==")
    print(req("POST", "/api/chat", {"message": "coffee 150 cash"}))
    print("== POST /api/chat (borrowed) ==")
    print(req("POST", "/api/chat", {"message": "borrowed 250 from Aivann"}))
