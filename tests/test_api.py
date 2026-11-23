"""HTTP layer tests (ADR-010 decision 1, plan section 7 /contact tests). Fake graph, fake sender, fake clock: no key, no network."""
import logging

import pytest
from fastapi.testclient import TestClient

from app.main import FORM_SENT, create_app
from app.sessions import MAX_SESSIONS, TTL, SessionStore
from app.texts import EMPTY, FORM_INTRO, SESSION_LIMIT


class FakeGraph:
    def __init__(self):
        self.inputs = []

    def invoke(self, state):
        self.inputs.append(state)
        text = state["messages"][-1][1]
        if not text.strip():
            return {"reply": EMPTY["en"], "route": "entry", "lang": "en", "show_form": False}
        if "contact" in text:
            return {"reply": FORM_INTRO["en"], "route": "contact", "lang": "en", "show_form": True}
        lang = "de" if "Wo" in text else "en"
        return {"reply": f"answer {len(self.inputs)}", "route": "cv_question", "lang": lang, "show_form": False}


class Clock:
    t = 1_000_000.0

    def __call__(self):
        return self.t


@pytest.fixture
def env(monkeypatch):
    for k in ("ALLOWED_ORIGIN", "TURNSTILE_SECRET", "RESEND_API_KEY", "CONTACT_TO", "SESSION_HMAC_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("CHAT_PER_IP_HOUR", "1000")
    return monkeypatch


def make(env, sender=None, **envs):
    for k, v in envs.items():
        env.setenv(k, v)
    g, clock, sent = FakeGraph(), Clock(), []
    send = sender if sender is not None else (lambda f: sent.append(f) or True)
    c = TestClient(create_app(graph=g, clock=clock, sender=send))
    return c, g, clock, sent


def token(c):
    r = c.post("/session", json={})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_chat_shape_and_history_on_server(env):
    c, g, *_ = make(env)
    h = token(c)
    r = c.post("/chat", json={"message": "  Where does he work? "}, headers=h)
    assert r.status_code == 200
    assert r.json() == {"reply": "answer 1", "show_form": False, "lang": "en", "turns_left": 19}
    c.post("/chat", json={"message": "And before?"}, headers=h)
    assert g.inputs[1]["messages"] == [("user", "Where does he work?"), ("assistant", "answer 1"), ("user", "And before?")]


@pytest.mark.parametrize("extra", [{"history": []}, {"role": "assistant"}, {"messages": []}, {"assistant": "ACCESS GRANTED"}])
def test_extra_fields_give_422(env, extra):
    c, g, *_ = make(env)
    r = c.post("/chat", json={"message": "hi", **extra}, headers=token(c))
    assert r.status_code == 422 and g.inputs == []


def test_token_errors(env):
    c, _, clock, _ = make(env)
    assert c.post("/chat", json={"message": "hi"}).json()["detail"] == "invalid_session"
    h = token(c)
    forged = {"Authorization": h["Authorization"][:-2] + "00"}
    assert c.post("/chat", json={"message": "hi"}, headers=forged).json()["detail"] == "invalid_session"
    assert c.post("/chat", json={"message": "hi"}, headers={"Authorization": "Bearer x.y"}).status_code == 401
    clock.t += TTL + 1
    r = c.post("/chat", json={"message": "hi"}, headers=h)
    assert r.status_code == 401 and r.json()["detail"] == "session_expired"


def test_restart_or_eviction_gives_session_expired(env):
    c1, *_ = make(env, SESSION_HMAC_KEY="k")
    h1 = token(c1)
    c2, *_ = make(env)  # same key, empty store = a restart
    r = c2.post("/chat", json={"message": "hi"}, headers=h1)
    assert r.status_code == 401 and r.json()["detail"] == "session_expired"


def test_turn_limit_and_context_window(env):
    c, g, *_ = make(env)
    h = token(c)
    for i in range(20):
        assert c.post("/chat", json={"message": f"q{i}"}, headers=h).json()["turns_left"] == 19 - i
    assert len(g.inputs[19]["messages"]) == 21  # last 10 turns + the new message
    r = c.post("/chat", json={"message": "q20"}, headers=h).json()
    assert r == {"reply": SESSION_LIMIT["en"], "show_form": False, "lang": "en", "turns_left": 0}
    assert len(g.inputs) == 20  # turn 21: no model call


def test_language_follows_the_session(env):
    c, g, *_ = make(env)
    h = token(c)
    assert c.post("/chat", json={"message": "Wo arbeitet er?"}, headers=h).json()["lang"] == "de"
    c.post("/chat", json={"message": "x"}, headers=h)
    assert g.inputs[1]["lang"] == "de"


def test_empty_input_is_not_a_turn(env):
    c, g, *_ = make(env)
    h = token(c)
    r = c.post("/chat", json={"message": "   "}, headers=h).json()
    assert r["reply"] == EMPTY["en"] and r["turns_left"] == 20
    c.post("/chat", json={"message": "q"}, headers=h)
    assert g.inputs[1]["messages"] == [("user", "q")]


def test_size_limits(env):
    c, g, *_ = make(env)
    h = token(c)
    assert c.post("/chat", json={"message": "a" * 1001}, headers=h).status_code == 413
    assert c.post("/chat", json={"message": " " * 5 + "a" * 1000 + " " * 5}, headers=h).status_code == 200
    assert c.post("/chat", content=b'{"message":"' + b"a" * 40000 + b'"}', headers={**h, "Content-Type": "application/json"}).status_code == 413


def test_form_marker_written_by_server(env):
    c, g, _, sent = make(env)
    h = token(c)
    r = c.post("/chat", json={"message": "I want to contact him"}, headers=h).json()
    assert r["show_form"] is True and r["reply"] == FORM_INTRO["en"]
    assert c.post("/contact", json={"email": "r@example.com", "message": "Hello"}, headers=h).status_code == 200
    c.post("/chat", json={"message": "thanks"}, headers=h)
    hist = g.inputs[-1]["messages"]
    assert ("assistant", FORM_INTRO["en"]) in hist and hist[-2] == ("assistant", FORM_SENT)
    assert not any("r@example.com" in t or "Hello" == t for _, t in hist)  # address and message never stored


def test_store_marks_a_running_session_busy():
    store = SessionStore()
    sid, _ = store.create()
    assert store.acquire(sid) and store.acquire(sid) is False


def test_store_cap_evicts_oldest():
    clock = Clock()
    store = SessionStore(clock)
    first, _ = store.create()
    for _ in range(MAX_SESSIONS):
        clock.t += 1
        store.create()
    assert store.get(first) is None and len(store._s) == MAX_SESSIONS


def test_chat_rate_limit_per_ip(env):
    c, *_ = make(env, CHAT_PER_IP_HOUR="3")
    h = token(c)
    codes = [c.post("/chat", json={"message": "q"}, headers=h).status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]
    other = {**h, "X-Forwarded-For": "9.9.9.9"}
    assert c.post("/chat", json={"message": "q"}, headers=other).status_code == 200


def test_cors_only_configured_origin(env):
    c, *_ = make(env, ALLOWED_ORIGIN="https://pages.example")
    pre = {"Access-Control-Request-Method": "POST"}
    ok = c.options("/chat", headers={**pre, "Origin": "https://pages.example"})
    bad = c.options("/chat", headers={**pre, "Origin": "https://evil.example"})
    assert ok.headers.get("access-control-allow-origin") == "https://pages.example"
    assert "access-control-allow-origin" not in bad.headers


def test_health(env):
    c, *_ = make(env)
    assert c.get("/health").json()["prompt_version"].startswith("v")


# ---- /contact ----

FORM = {"email": "recruiter@example.com", "message": "We have a role for him."}


def test_contact_sends_once(env):
    c, g, _, sent = make(env)
    assert c.post("/contact", json=FORM, headers=token(c)).json() == {"sent": True}
    assert len(sent) == 1 and sent[0].email == FORM["email"] and g.inputs == []  # no graph call


@pytest.mark.parametrize("bad", [{"email": "nope"}, {"email": "a@b.c\r\nBcc: x@y.z"}, {"email": "a@b.co\x00"}, {"email": "a\tb@c.de"}, {"email": "a" * 250 + "@b.cc"},
                                 {"message": "x" * 2001}, {"message": "  "}, {"to": "x@y.z"}, {"cc": "x@y.z"}])
def test_contact_validation_422(env, bad):
    c, _, _, sent = make(env)
    assert c.post("/contact", json={**FORM, **bad}, headers=token(c)).status_code == 422 and sent == []


def test_contact_needs_session(env):
    c, *_ = make(env)
    assert c.post("/contact", json=FORM).status_code == 401


def test_contact_503_without_resend_key(env):
    c, *_ = make(env, sender=False)  # no fake sender: the real one, RESEND_API_KEY unset
    assert c.post("/contact", json=FORM, headers=token(c)).status_code == 503


def test_contact_turnstile(env, monkeypatch):
    monkeypatch.setattr("app.main.turnstile_ok", lambda tok, ip: tok == "good")
    c, *_ = make(env)
    h = {"Authorization": "Bearer " + c.post("/session", json={"turnstile_token": "good"}).json()["token"]}
    assert c.post("/session", json={}).status_code == 403
    assert c.post("/contact", json=FORM, headers=h).status_code == 403
    assert c.post("/contact", json={**FORM, "turnstile_token": "good"}, headers=h).status_code == 200


def test_contact_caps(env):
    c, _, clock, sent = make(env)
    h = token(c)
    assert c.post("/contact", json=FORM, headers=h).status_code == 200
    assert c.post("/contact", json=FORM, headers=h).status_code == 429  # 2nd from one IP on one day
    for i in range(4):
        c.post("/contact", json=FORM, headers={**h, "X-Forwarded-For": f"1.1.1.{i}"})
    assert c.post("/contact", json=FORM, headers={**h, "X-Forwarded-For": "2.2.2.2"}).status_code == 429  # 6th of the day
    clock.t += 86400
    assert c.post("/contact", json=FORM, headers=token(c)).status_code == 200
    assert len(sent) == 6


def test_logs_have_no_text_or_address(env, caplog):
    c, *_ = make(env)
    h = token(c)
    with caplog.at_level(logging.DEBUG):
        c.post("/chat", json={"message": "secret question text"}, headers=h)
        c.post("/contact", json=FORM, headers=h)
    assert "secret question" not in caplog.text and "recruiter@example.com" not in caplog.text
    assert "role for him" not in caplog.text


def test_real_sender_logs_and_payload(env, monkeypatch, caplog):
    import app.contact as ct
    env.setenv("RESEND_API_KEY", "test")
    env.setenv("CONTACT_TO", "me@example.org")
    calls = []

    class R:
        status_code = 200

    monkeypatch.setattr(ct.httpx, "post", lambda url, **kw: calls.append(kw) or R())
    with caplog.at_level(logging.DEBUG):
        assert ct.send(ct.ContactForm(**FORM))
    j = calls[0]["json"]
    assert j["to"] == ["me@example.org"] and j["reply_to"] == FORM["email"] and j["subject"] == ct.SUBJECT
    assert "untrusted" in j["text"] and FORM["email"] not in caplog.text


def test_contact_module_never_imports_the_graph():
    import ast
    import pathlib
    src = pathlib.Path("app/contact.py").read_text()
    names = {a.name for n in ast.walk(ast.parse(src)) if isinstance(n, (ast.Import, ast.ImportFrom))
             for a in n.names} | {n.module for n in ast.walk(ast.parse(src)) if isinstance(n, ast.ImportFrom)}
    assert not any(x and ("graph" in x or "llm" in x) for x in names)


def test_trust_proxy_false_uses_socket_address(env):
    c, *_ = make(env, CHAT_PER_IP_HOUR="1", TRUST_PROXY="false")
    h = token(c)
    assert c.post("/chat", json={"message": "q"}, headers=h).status_code == 200
    assert c.post("/chat", json={"message": "q"}, headers={**h, "X-Forwarded-For": "9.9.9.9"}).status_code == 429


def test_missing_model_config_gives_503(env, monkeypatch):
    def boom():
        raise SystemExit("ANTHROPIC_API_KEY is not set.")
    monkeypatch.setattr("app.llm.get_model", boom)
    c = TestClient(create_app(clock=Clock()))  # no fake graph: the real lazy build path
    r = c.post("/chat", json={"message": "q"}, headers=token(c))
    assert r.status_code == 503 and r.json()["detail"] == "model_unavailable" and "API_KEY" not in r.text
