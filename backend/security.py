"""
SaulGPT: request security (default-deny).

One FastAPI dependency, attached to the app itself, runs before EVERY route, including
routes copied into another app by app.py (a plain @app.middleware would not be copied).

 * every /api/* route needs a valid login unless it is in PUBLIC_ROUTES (default-deny)
 * a login token is read from X-SaulGPT-Token or "Authorization: Bearer"
 * the user's own Groq key (X-Groq-Api-Key) is applied per request and REQUIRED on AI routes;
   the server's key is never used unless ALLOW_SERVER_GROQ_KEY=1
 * rate limits: by IP on login/signup, by user on everything else (AI routes much lower)
 * downloads (document / certificate) also accept a signed, expiring ?t= link
"""
import ipaddress
import os
import re
import threading
import time
from collections import defaultdict, deque
from typing import Optional

from fastapi import HTTPException, Request

from auth import decode_token, link_token_ok
from key_context import set_request_groq_key

PUBLIC_ROUTES = {("GET", "/api/health"), ("POST", "/api/auth/signup"), ("POST", "/api/auth/login")}
LINK_PREFIXES = ("/api/document/", "/api/certificates/")
AI_PREFIXES = ("/api/chat", "/api/upload", "/api/evidence/upload", "/api/bench/", "/api/trial/", "/api/test/")
SID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,100}$")

AUTH_PER_MIN = 20       # login/signup per IP
AI_PER_MIN = 20         # AI routes per user (each answer takes minutes, so this is generous)
GENERAL_PER_MIN = 120   # everything else per user
KEY_MSG = ("Groq API Key is required. Please provide your free Groq API Key (starts with 'gsk_') "
           "from console.groq.com/keys via the API Key button in the top bar.")


class Limiter:
    """Sliding-window counter. In-memory: correct for one server process (a Space is one)."""

    def __init__(self):
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def retry_after(self, key: str, limit: int, window: float) -> int:
        """0 if the call is allowed (and counted), else seconds until it would be."""
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > window:
                q.popleft()
            if len(q) >= limit:
                return int(window - (now - q[0])) + 1
            q.append(now)
            if len(self._hits) > 20000:  # bound memory: drop idle keys
                for k in [k for k, v in self._hits.items() if not v or now - v[-1] > window]:
                    del self._hits[k]
        return 0


limiter = Limiter()


def client_ip(request: Request) -> str:
    """Right-most PUBLIC address in X-Forwarded-For (the part a client cannot forge), else the socket peer."""
    for part in reversed([p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]):
        try:
            if ipaddress.ip_address(part).is_global:
                return part
        except ValueError:
            continue
    return request.client.host if request.client else "unknown"


def _token(request: Request) -> str:
    t = request.headers.get("x-saulgpt-token", "").strip()
    if t:
        return t
    scheme, _, value = request.headers.get("authorization", "").partition(" ")
    return value.strip() if scheme.lower() == "bearer" else ""


def _too_many(seconds: int):
    raise HTTPException(429, f"Too many requests. Please wait {seconds}s and try again.",
                        headers={"Retry-After": str(seconds)})


def user_key_ok(request: Request) -> bool:
    return request.headers.get("x-groq-api-key", "").strip().startswith("gsk_")


async def security_guard(request: Request) -> None:
    path = request.url.path
    if request.method == "OPTIONS" or not path.startswith("/api/"):
        return

    # Per-request Groq key: set it HERE so it works however the app is mounted.
    key = request.headers.get("x-groq-api-key", "").strip()
    set_request_groq_key(key if key.startswith("gsk_") else None)
    request.state.user_id = None

    if (request.method, path) in PUBLIC_ROUTES:
        if path != "/api/health" and (wait := limiter.retry_after(f"auth:{client_ip(request)}", AUTH_PER_MIN, 60)):
            _too_many(wait)
        return

    uid = decode_token(_token(request))
    if uid is None:
        t = request.query_params.get("t", "")
        if path.startswith(LINK_PREFIXES) and t and link_token_ok(t, path):
            return  # signed download link
        print(f"[Auth] 401 {request.method} {path} token_header={'yes' if _token(request) else 'no'}")
        raise HTTPException(401, "Please sign in again.")
    request.state.user_id = uid

    ai = path.startswith(AI_PREFIXES)
    if wait := limiter.retry_after(f"{'ai' if ai else 'gen'}:{uid}", AI_PER_MIN if ai else GENERAL_PER_MIN, 60):
        _too_many(wait)
    if ai and not user_key_ok(request) and os.getenv("ALLOW_SERVER_GROQ_KEY") != "1":
        raise HTTPException(400, KEY_MSG)


def scope_sid(request: Request, raw: Optional[str]) -> str:
    """Make a client-supplied session id private to the signed-in user (and filename-safe)."""
    if not raw or not SID_RE.fullmatch(raw):
        raise HTTPException(400, "Invalid session id.")
    return f"u{request.state.user_id}_{raw}"
