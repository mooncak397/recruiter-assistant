"""HTTP-layer guards (plan section 6): session token, rate limits, Turnstile, client IP.
The answer guards inside the graph live in app/answer_guards.py."""
import base64
import hashlib
import hmac
import logging
import os
import secrets
import threading
import time

import httpx

log = logging.getLogger(__name__)
TURNSTILE_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


class Tokens:
    """Token = base64url("sid.exp") + "." + HMAC-SHA256. No key set: a random key per process,
    which is fine because a restart deletes the in-memory sessions anyway."""

    def __init__(self, key: str | None = None, clock=time.time):
        self.key = (key or secrets.token_hex(32)).encode()
        self.clock = clock

    def _sig(self, body: str) -> str:
        return hmac.new(self.key, body.encode(), hashlib.sha256).hexdigest()

    def make(self, sid: str, exp: float) -> str:
        body = base64.urlsafe_b64encode(f"{sid}.{int(exp)}".encode()).decode()
        return f"{body}.{self._sig(body)}"

    def check(self, token: str) -> tuple[str | None, str | None]:
        """(sid, None) if valid, else (None, "invalid_session" | "session_expired")."""
        try:
            body, sig = token.rsplit(".", 1)
            if not hmac.compare_digest(sig, self._sig(body)):
                return None, "invalid_session"
            sid, exp = base64.urlsafe_b64decode(body.encode()).decode().rsplit(".", 1)
            if int(exp) <= self.clock():
                return None, "session_expired"
            return sid, None
        except ValueError:  # bad base64, missing dot, bad number
            return None, "invalid_session"


class Limiter:
    """Fixed-window counter per key (an IP or "global").
    shortcut: windows start at the first hit, not at midnight UTC; fine for abuse caps on one worker."""

    def __init__(self, limit: int, window: float, clock=time.time):
        self.limit, self.window, self.clock = limit, window, clock
        self._lock = threading.Lock()
        self._hits: dict[str, tuple[float, int]] = {}

    def hit(self, key: str) -> bool:
        """Count one hit. False = over the limit (the hit is not counted)."""
        now = self.clock()
        with self._lock:
            if len(self._hits) > 10_000:  # keep memory bounded: drop finished windows
                self._hits = {k: v for k, v in self._hits.items() if now - v[0] < self.window}
            start, n = self._hits.get(key, (now, 0))
            if now - start >= self.window:
                start, n = now, 0
            if n >= self.limit:
                return False
            self._hits[key] = (start, n + 1)
            return True


def client_ip(headers, peer: str | None) -> str:
    # TRUST_PROXY (default true: the Space is behind the HF proxy): the LAST X-Forwarded-For entry
    # is the one the proxy added; earlier entries come from the client and can be forged.
    # Without a proxy any client can set the header, so TRUST_PROXY=false uses the socket address only.
    xff = headers.get("x-forwarded-for")
    if xff and os.environ.get("TRUST_PROXY", "true").lower() not in ("0", "false", "no"):
        return xff.split(",")[-1].strip()
    return peer or "unknown"


def turnstile_ok(token: str | None, ip: str) -> bool:
    """Cloudflare Turnstile check. TURNSTILE_SECRET unset (dev): skipped."""
    secret = os.environ.get("TURNSTILE_SECRET")
    if not secret:
        return True
    if not token:
        return False
    try:
        r = httpx.post(TURNSTILE_URL, data={"secret": secret, "response": token, "remoteip": ip}, timeout=10)
        return bool(r.json().get("success"))
    except (httpx.HTTPError, ValueError) as e:  # fail closed
        log.warning("turnstile_error class=%s", type(e).__name__)
        return False
