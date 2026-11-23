"""FastAPI app (plan section 3, ADR-010 decision 1). Run with exactly 1 worker: sessions live in process memory.
  uv run uvicorn app.main:app --port 7860 --workers 1 --no-proxy-headers"""
import logging
import os
import threading
import time

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from app import contact as contact_mod
from app.guards import Limiter, Tokens, client_ip, turnstile_ok
from app.prompts import rules_version
from app.sessions import MAX_TURNS, TTL, SessionStore
from app.texts import BUSY, EMPTY, SESSION_LIMIT

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")  # Space logs: no message text
log = logging.getLogger("app.main")
MAX_BODY = 32 * 1024
MAX_CHARS = 1000
HOUR, DAY = 3600, 86400
FORM_SENT = "(contact form sent)"  # server-written marker, the client never sends one


class ChatIn(BaseModel):
    model_config = ConfigDict(extra="forbid")  # `history`, `role`, `assistant`, markers: 422
    message: str


class SessionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    turnstile_token: str | None = None


def create_app(graph=None, clock=time.time, sender=None) -> FastAPI:
    """graph and sender are injectable for tests; by default the real graph is built on the first /chat."""
    app = FastAPI(title="Recruiter assistant", docs_url=None, redoc_url=None, openapi_url=None)
    origin = os.environ.get("ALLOWED_ORIGIN")
    app.add_middleware(CORSMiddleware, allow_origins=[origin] if origin else [],
                       allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"])
    store = SessionStore(clock)
    tokens = Tokens(os.environ.get("SESSION_HMAC_KEY"), clock)
    env = lambda k, d: int(os.environ.get(k, d))  # noqa: E731
    lim = {"session_ip": Limiter(env("SESSIONS_PER_IP_HOUR", 10), HOUR, clock),
           "chat_ip": Limiter(env("CHAT_PER_IP_HOUR", 20), HOUR, clock),
           "chat_day": Limiter(env("CHAT_PER_DAY", 140), DAY, clock),
           "contact_ip": Limiter(env("CONTACT_PER_IP_DAY", 1), DAY, clock),
           "contact_day": Limiter(env("CONTACT_PER_DAY", 5), DAY, clock)}
    send = sender or contact_mod.send
    state = {"graph": graph}
    graph_lock = threading.Lock()

    def get_graph():
        with graph_lock:
            if state["graph"] is None:
                from app.graph import build_graph
                from app.llm import get_model
                state["graph"] = build_graph(get_model())
            return state["graph"]

    @app.middleware("http")
    async def body_limit(request: Request, call_next):
        if request.method == "POST":
            n = request.headers.get("content-length")
            if n is None:  # no chunked uploads: we could not cap them before reading
                return JSONResponse({"detail": "length_required"}, 411)
            if not n.isdigit() or int(n) > MAX_BODY:
                return JSONResponse({"detail": "too_large"}, 413)
        return await call_next(request)

    def get_ip(request: Request) -> str:
        return client_ip(request.headers, request.client.host if request.client else None)

    def sid_from(request: Request) -> str:
        auth = request.headers.get("authorization", "")
        if not auth.startswith("Bearer "):
            raise HTTPException(401, "invalid_session")
        sid, err = tokens.check(auth[7:].strip())
        if err:
            raise HTTPException(401, err)
        return sid

    @app.get("/health")
    def health():
        return {"status": "ok", "prompt_version": rules_version()}

    @app.post("/session")
    def new_session(body: SessionIn, ip: str = Depends(get_ip)):
        if not lim["session_ip"].hit(ip):
            raise HTTPException(429, "rate_limited")
        if not turnstile_ok(body.turnstile_token, ip):
            raise HTTPException(403, "turnstile_failed")
        sid, exp = store.create()
        return {"token": tokens.make(sid, exp), "expires_in": TTL, "turns_left": MAX_TURNS}

    @app.post("/chat")
    def chat(body: ChatIn, sid: str = Depends(sid_from), ip: str = Depends(get_ip)):
        if not lim["chat_ip"].hit(ip):
            raise HTTPException(429, "rate_limited")
        text = body.message.strip()
        if len(text) > MAX_CHARS:
            raise HTTPException(413, "message_too_long")
        s = store.acquire(sid)
        if s is None:
            raise HTTPException(401, "session_expired")
        if s is False:
            raise HTTPException(409, "busy")
        try:
            if s.turns >= MAX_TURNS:  # no model call
                return {"reply": SESSION_LIMIT[s.lang], "show_form": False, "lang": s.lang, "turns_left": 0}
            if not lim["chat_day"].hit("global"):
                raise HTTPException(429, "daily_limit")
            t0 = time.time()
            try:
                graph = get_graph()
            except SystemExit as e:  # app/llm.py: model name or key missing; a config error, not a crash
                log.error("model_config_missing %s", type(e).__name__)
                return JSONResponse({"detail": "model_unavailable", "reply": BUSY[s.lang]}, 503)
            out = graph.invoke({"messages": [*store.context(s), ("user", text)], "lang": s.lang})
            reply, lang = out["reply"], out["lang"]
            log.info("chat route=%s lang=%s form=%s ms=%d", out["route"], lang, out["show_form"],
                     (time.time() - t0) * 1000)
            if not (out["route"] == "entry" and reply == EMPTY[lang]):  # empty input: not stored, not a turn
                # the stored reply is the finalize output; when the form opens it is the fixed FORM_INTRO
                s.messages += [("user", text), ("assistant", reply)]
                s.turns += 1
                s.lang = lang
            return {"reply": reply, "show_form": bool(out["show_form"]), "lang": lang,
                    "turns_left": MAX_TURNS - s.turns}
        finally:
            store.release(s)

    @app.post("/contact")
    def contact(form: contact_mod.ContactForm, sid: str = Depends(sid_from), ip: str = Depends(get_ip)):
        if not turnstile_ok(form.turnstile_token, ip):
            raise HTTPException(403, "turnstile_failed")
        if not (sender or contact_mod.configured()):
            raise HTTPException(503, "contact_disabled")
        if not lim["contact_ip"].hit(ip) or not lim["contact_day"].hit("global"):
            raise HTTPException(429, "rate_limited")
        if not send(form):
            raise HTTPException(502, "send_failed")
        if s := store.get(sid):  # the marker only: the address and the message are never stored
            s.messages.append(("assistant", FORM_SENT))
        return {"sent": True}

    return app


app = create_app()
