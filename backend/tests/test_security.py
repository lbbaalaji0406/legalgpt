"""Security regression tests for the public SaulGPT API (no network, no real AI calls).

Run: python -m pytest backend/tests/test_security.py -q
"""
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone

os.environ["GROQ_API_KEY"] = "server-key-must-never-be-used"
os.environ.pop("ALLOW_SERVER_GROQ_KEY", None)
os.environ.pop("DATABASE_URL", None)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import database  # noqa: E402
database.DB_PATH = os.path.join(tempfile.mkdtemp(), "test.db")  # never touch a real database
database.init_db()

import pytest  # noqa: E402
from fastapi.routing import APIRoute  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from jose import jwt  # noqa: E402

import auth  # noqa: E402
import security  # noqa: E402
from api_server import app, SESSION_DOCUMENTS  # noqa: E402

client = TestClient(app)
KEY = {"X-Groq-Api-Key": "gsk_test_user_key"}
_n = [0]


def _ip():
    """A fresh public IP per call so tests never share a rate-limit bucket."""
    _n[0] += 1
    return {"X-Forwarded-For": f"8.8.{_n[0] // 250}.{_n[0] % 250 + 1}"}


def signup(email=None, pw="Str0ng-pass"):
    _n[0] += 1
    r = client.post("/api/auth/signup", json={"email": email or f"t{_n[0]}@x.in", "password": pw}, headers=_ip())
    assert r.status_code == 200, r.text
    d = r.json()
    return d["user_id"], {"X-SaulGPT-Token": d["token"]}


def test_every_api_route_requires_login():
    """Default-deny: any /api route not on the public list must answer 401 without a login."""
    open_routes = []
    for route in app.routes:
        if not isinstance(route, APIRoute) or not route.path.startswith("/api/"):
            continue
        for method in route.methods - {"HEAD", "OPTIONS"}:
            if (method, route.path) in security.PUBLIC_ROUTES:
                continue
            url = route.path.replace("{conv_id}", "1")
            for name in ("session_id", "cert_filename", "case_id", "term_name", "mode"):
                url = url.replace("{%s}" % name, "x")
            r = client.request(method, url, headers=_ip())
            if r.status_code != 401:
                open_routes.append(f"{method} {route.path} -> {r.status_code}")
    assert not open_routes, "routes reachable without login: " + "; ".join(open_routes)


def test_guard_survives_app_py_mounting():
    """app.py copies this app's routes into Gradio's app. A plain middleware is NOT copied (that is how
    the old BYOK check silently never ran in production); the route dependency must be."""
    from fastapi import FastAPI
    outer = FastAPI()
    outer.include_router(app.router)
    c = TestClient(outer)
    assert c.get("/api/conversations", headers=_ip()).status_code == 401
    assert c.get("/api/test/agents", headers=_ip()).status_code == 401
    _, h = signup()
    assert c.get("/api/trial/search?query=x", headers=h).status_code == 400  # key required on the mounted copy too


def test_public_routes_are_only_health_signup_login():
    assert security.PUBLIC_ROUTES == {("GET", "/api/health"), ("POST", "/api/auth/signup"), ("POST", "/api/auth/login")}


def test_token_forged_with_the_old_published_secret_is_rejected():
    uid, _ = signup()
    forged = jwt.encode({"sub": str(uid), "exp": datetime.now(timezone.utc) + timedelta(days=1)},
                        "saulgpt-dev-secret-change-in-production-2024", algorithm="HS256")
    assert client.get("/api/auth/me", headers={"X-SaulGPT-Token": forged, **_ip()}).status_code == 401
    assert auth.SECRET_KEY != "saulgpt-dev-secret-change-in-production-2024" and len(auth.SECRET_KEY) >= 32


def test_token_accepted_in_either_header_and_me_is_the_real_user():
    uid, h = signup()
    assert client.get("/api/auth/me", headers=h).json()["user_id"] == uid
    bearer = {"Authorization": "Bearer " + h["X-SaulGPT-Token"]}
    assert client.get("/api/auth/me", headers=bearer).json()["user_id"] == uid


def test_a_download_link_token_is_not_a_login():
    uid, _ = signup()
    link = auth.make_link_token("/api/document/u1_x")
    assert client.get("/api/auth/me", headers={"X-SaulGPT-Token": link, **_ip()}).status_code == 401


def test_ai_routes_need_the_users_own_groq_key_never_the_server_key():
    _, h = signup()
    r = client.get("/api/trial/search?query=cheque", headers=h)
    assert r.status_code == 400 and "Groq API Key" in r.json()["detail"]
    assert client.get("/api/trial/search?query=cheque", headers={**h, "X-Groq-Api-Key": "not-a-groq-key"}).status_code == 400
    assert client.get("/api/trial/search?query=cheque", headers={**h, **KEY}).status_code != 400


def test_signup_input_rules():
    for body in ({"email": "nope", "password": "Str0ng-pass"}, {"email": "a@b.in", "password": "short"},
                 {"email": "a@b.in", "password": "x" * 73}, {"email": "a@b.in", "password": "Str0ng-pass", "username": "u" * 51}):
        assert client.post("/api/auth/signup", json=body, headers=_ip()).status_code == 400, body


def test_password_guessing_is_limited_but_cannot_lock_out_the_real_user():
    email = "victim@x.in"
    signup(email, "Victim-pass-1")
    attacker = _ip()
    codes = [client.post("/api/auth/login", json={"email": email, "password": "wrong-pass"}, headers=attacker).status_code for _ in range(12)]
    assert codes[:security.LOGIN_TRIES_PER_IP] == [401] * security.LOGIN_TRIES_PER_IP and codes[-1] == 429
    ok = client.post("/api/auth/login", json={"email": email, "password": "Victim-pass-1"}, headers=_ip())
    assert ok.status_code == 200  # the real user, from their own IP, is not locked out
    spread = [client.post("/api/auth/login", json={"email": email, "password": "wrong"}, headers=_ip()).status_code
              for _ in range(security.LOGIN_TRIES_PER_ACCOUNT + 2)]  # botnet: one try per IP
    assert spread[-1] == 429  # still capped per account


def test_auth_and_signups_are_limited_per_ip():
    ip = _ip()
    codes = [client.post("/api/auth/login", json={"email": f"u{i}@x.in", "password": "p"}, headers=ip).status_code for i in range(22)]
    assert codes[-1] == 429 and 429 not in codes[:security.AUTH_PER_MIN]
    ip = _ip()
    codes = [client.post("/api/auth/signup", json={"email": f"many{i}@x.in", "password": "Str0ng-pass"}, headers=ip).status_code
             for i in range(security.SIGNUPS_PER_HOUR + 1)]
    assert codes[:-1] == [200] * security.SIGNUPS_PER_HOUR and codes[-1] == 429


def test_certificates_need_the_uploaders_signed_link_not_just_a_login():
    _, h = signup()
    path = "/api/certificates/BSA63-DOC-ABCDEF12.pdf"
    assert client.get(path, headers=h).status_code == 401                     # another signed-in user, no link
    assert client.get(f"{path}?t={auth.make_link_token(path)}", headers=_ip()).status_code != 401


def test_ai_routes_are_rate_limited_per_user():
    _, h = signup()
    codes = [client.get("/api/trial/search?query=x", headers={**h, **KEY}).status_code for _ in range(security.AI_PER_MIN + 2)]
    assert codes[-1] == 429 and 429 not in codes[:security.AI_PER_MIN]
    assert client.get("/api/trial/search?query=x", headers={**h, **KEY}).json()["detail"].startswith("Too many requests")


def test_session_state_is_private_to_each_user():
    from pipeline_orchestrator import CONVERSATION_MEMORY
    a, ha = signup()
    _, hb = signup()
    CONVERSATION_MEMORY[f"u{a}_s1"] = [{"q": "private question"}]
    assert client.get("/api/history/s1", headers=ha).json()["turns"] == 1
    assert client.get("/api/history/s1", headers=hb).json()["turns"] == 0        # same raw id, other user
    assert client.get(f"/api/history/session_conv_{a}", headers=hb).json()["turns"] == 0
    assert client.get("/api/history/a%20b", headers=ha).status_code == 400         # not filename-safe
    assert client.get("/api/history/..%2Fetc", headers=ha).status_code in (400, 404)


def test_documents_only_for_owner_or_signed_link():
    a, ha = signup()
    _, hb = signup()
    sid = f"u{a}_s1"
    SESSION_DOCUMENTS[sid] = b"DOCX-BYTES"
    path = f"/api/document/{sid}"
    assert client.get(path, headers=ha).content == b"DOCX-BYTES"
    assert client.get(path, headers=hb).status_code == 404
    assert client.get(path, headers=_ip()).status_code == 401
    assert client.get(f"{path}?t={auth.make_link_token(path)}", headers=_ip()).content == b"DOCX-BYTES"
    assert client.get(f"{path}?t={auth.make_link_token('/api/document/u999_other')}", headers=_ip()).status_code == 401
    expired = jwt.encode({"sub": f"link:{path}", "exp": datetime.now(timezone.utc) - timedelta(seconds=5)}, auth.SECRET_KEY, algorithm="HS256")
    assert client.get(f"{path}?t={expired}", headers=_ip()).status_code == 401


def test_ai_clients_use_the_requests_key_never_the_servers():
    """Every AI client must be built per request with the user's key (a client built at import would
    pin the server's key for every user)."""
    from key_context import set_request_groq_key
    from agents import llm_client
    from agents.researcher import ResearcherAgent
    from agents.drafter import DrafterAgent
    from agents.reviewer import ReviewerAgent
    from agents.triage import TriageAgent

    def key_of(llm):
        return getattr(llm, "runnable", llm).groq_api_key.get_secret_value()

    assert not hasattr(llm_client, "researcher")  # no import-time instances any more
    set_request_groq_key("gsk_alice")
    factories = [llm_client.get_researcher_llm, llm_client.get_drafter_llm, llm_client.get_reviewer_llm,
                 llm_client.get_triage_llm, llm_client.get_advocate_llm, llm_client.get_binary_gate_llm,
                 llm_client.get_discovery_llm]
    assert {key_of(f()) for f in factories} == {"gsk_alice"}
    agents = [ResearcherAgent(), DrafterAgent(), ReviewerAgent(), TriageAgent()]
    assert {key_of(a.llm) for a in agents} == {"gsk_alice"}
    set_request_groq_key("gsk_bob")                       # same agent objects, next request
    assert {key_of(a.llm) for a in agents} == {"gsk_bob"}
    set_request_groq_key(None)


def test_client_ip_uses_the_rightmost_public_address():
    class R:  # minimal stand-in for a Request
        def __init__(self, xff, peer="10.0.0.1"):
            self.headers = {"x-forwarded-for": xff}
            self.client = type("C", (), {"host": peer})()
    assert security.client_ip(R("1.2.3.4, 9.9.9.9")) == "9.9.9.9"          # client cannot choose the last hop
    assert security.client_ip(R("1.2.3.4, 9.9.9.9, 10.1.1.1")) == "9.9.9.9"  # internal proxy hop skipped
    assert security.client_ip(R("")) == "10.0.0.1"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
