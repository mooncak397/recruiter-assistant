"""Fake backend for testing web/ locally. Stdlib only, no model calls. Mirrors the contract of app/main.py.

Run: python web/dev/fake_api.py [turns] [--turnstile]  (http://localhost:8787, default 20 turns)
  --turnstile: /session and /contact need a turnstile_token (like a backend with TURNSTILE_SECRET set)

Test triggers inside a chat message:
  !409 / !429 / !500 -> that status   !401 -> forget the session (next call gets 401 session_expired)
  contact / reach / kontakt / erreichen -> show_form true
  <b>html</b> -> echoed back, so you can check it renders as plain text
In the contact form, a message containing !503 or !500 gives that status.
"""
import json
import secrets
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TURNS = next((int(a) for a in sys.argv[1:] if a.isdigit()), 20)  # e.g. 6 to see the turns-left hint at once
TURNSTILE = "--turnstile" in sys.argv
sessions: dict[str, int] = {}  # token -> user turns used


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            return self._send(200, {"status": "ok", "prompt_version": "fake"})
        self._send(404, {"detail": "not found"})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        if self.path == "/session":
            if not set(body) <= {"turnstile_token"}:
                return self._send(422, {"detail": "extra fields"})
            if TURNSTILE and not body.get("turnstile_token"):
                return self._send(403, {"detail": "turnstile_failed"})
            token = secrets.token_urlsafe(16)
            sessions[token] = 0
            return self._send(200, {"token": token, "expires_in": 1800, "turns_left": TURNS})
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return self._send(401, {"detail": "invalid_session"})
        token = auth[7:]
        if token not in sessions:
            return self._send(401, {"detail": "session_expired"})
        if self.path == "/chat":
            return self.chat(token, body)
        if self.path == "/contact":
            return self.contact(body)
        self._send(404, {"detail": "not found"})

    def chat(self, token, body):
        if set(body) != {"message"}:
            return self._send(422, {"detail": "extra fields"})
        msg = str(body["message"]).strip()
        time.sleep(0.6)  # feel like a model call
        for code in (409, 429, 500):
            if f"!{code}" in msg:
                return self._send(code, {"detail": "test"})
        if len(msg) > 1000:
            return self._send(413, {"detail": "message_too_long"})
        low = msg.lower()
        de = any(w in low for w in ("ist", "er ", "welche", "wie", "kann", "kontakt", "ä", "ö", "ü"))
        lang = "de" if de else "en"
        if sessions[token] >= TURNS:
            return self._send(200, {"reply": "This chat has reached its limit.", "show_form": False, "lang": lang, "turns_left": 0})
        sessions[token] += 1
        form = any(w in low for w in ("contact", "reach", "kontakt", "erreichen"))
        if form:
            reply = ("Gern. Bitte nutzen Sie das Kontaktformular unten, um Christopher eine Nachricht zu senden." if de
                     else "Happy to help. Please use the contact form below to send Christopher a message.")
        elif "<" in msg:
            reply = f"Echo: {msg}"
        else:
            reply = ("Christopher arbeitet als Entwickler.\nDies ist eine Testantwort der Fake-API." if de
                     else "Christopher works as a developer.\nThis is a test reply from the fake API.")
        turns_left = TURNS - sessions[token]
        if "!401" in msg:
            sessions.pop(token)
        self._send(200, {"reply": reply, "show_form": form, "lang": lang, "turns_left": turns_left})

    def contact(self, body):
        time.sleep(0.6)
        if not set(body) <= {"email", "message", "turnstile_token"}:
            return self._send(422, {"detail": "extra fields"})
        if TURNSTILE and not body.get("turnstile_token"):
            return self._send(403, {"detail": "turnstile_failed"})
        for code in (500, 503):
            if f"!{code}" in str(body.get("message", "")):
                return self._send(code, {"detail": "test"})
        if "@" not in str(body.get("email", "")) or not body.get("message"):
            return self._send(422, {"detail": "invalid"})
        self._send(200, {"sent": True})

    def log_message(self, fmt, *args):  # request line only
        print(self.command, self.path, args[1] if len(args) > 1 else "")


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8787), Handler).serve_forever()
