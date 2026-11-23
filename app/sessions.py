"""In-memory chat history per session (ADR-010 decision 1).
Process memory: uvicorn must run with exactly 1 worker. A restart deletes all sessions."""
import secrets
import threading
import time
from dataclasses import dataclass, field

TTL = 30 * 60  # seconds, absolute, the same as the session token
MAX_SESSIONS = 500
MAX_TURNS = 20  # stored user turns; turn 21 gets SESSION_LIMIT
CONTEXT_TURNS = 10  # last turns that go to the model


@dataclass
class Session:
    expires_at: float
    messages: list[tuple[str, str]] = field(default_factory=list)  # ("user" | "assistant", text)
    lang: str = "en"
    turns: int = 0
    busy: bool = False


class SessionStore:
    def __init__(self, clock=time.time):
        self.clock = clock
        self._lock = threading.Lock()
        self._s: dict[str, Session] = {}

    def _sweep(self):
        now = self.clock()
        for sid in [k for k, v in self._s.items() if v.expires_at <= now]:
            del self._s[sid]

    def create(self) -> tuple[str, float]:
        with self._lock:
            self._sweep()
            if len(self._s) >= MAX_SESSIONS:  # full: evict the session that expires first
                del self._s[min(self._s, key=lambda k: self._s[k].expires_at)]
            sid, exp = secrets.token_urlsafe(16), self.clock() + TTL
            self._s[sid] = Session(expires_at=exp)
            return sid, exp

    def get(self, sid: str) -> Session | None:
        with self._lock:
            self._sweep()
            return self._s.get(sid)

    def acquire(self, sid: str) -> Session | None | bool:
        """The session, marked busy. None = unknown or expired, False = a request for it is running."""
        with self._lock:
            self._sweep()
            s = self._s.get(sid)
            if s is None:
                return None
            if s.busy:
                return False
            s.busy = True
            return s

    def release(self, s: Session):
        with self._lock:
            s.busy = False

    @staticmethod
    def context(s: Session) -> list[tuple[str, str]]:
        return s.messages[-2 * CONTEXT_TURNS:]
