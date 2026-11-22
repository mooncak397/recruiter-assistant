"""Step 2a (ADR-010 transport: no client assistant turns): every case through the real graph N times (default 3), 8 in parallel -> out/runs.jsonl (resumable).
Env: PROVIDER_APP=anthropic MODEL_APP=claude-haiku-5-5."""
import contextvars
import json
import logging
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from common import HERE, OUT, ROOT, guard, log, spend  # noqa: E402

sys.path.insert(0, str(ROOT))
from langchain_core.callbacks import BaseCallbackHandler  # noqa: E402

from app.graph import build_graph  # noqa: E402
from app.llm import get_model  # noqa: E402

RUNS = int(os.environ.get("RUNS", "3"))
FILE = OUT / "runs.jsonl"
MODEL = os.environ["MODEL_APP"]
_lock = threading.Lock()
_events = contextvars.ContextVar("events", default=None)


class Capture(logging.Handler):
    """Collects the graph's guard / model_error log lines for the current job (contextvars follow LangGraph's threads)."""
    def emit(self, record):
        ev = _events.get()
        if ev is not None:
            ev.append(record.getMessage())


logging.getLogger("app.graph").addHandler(Capture())
logging.getLogger("app.graph").setLevel(logging.INFO)


class Usage(BaseCallbackHandler):
    def __init__(self):
        self.n = 0

    def on_chat_model_start(self, *a, **k):
        self.n += 1

    def on_llm_end(self, response, **k):
        for g in response.generations:
            u = getattr(g[0].message, "usage_metadata", None) if g else None
            if u:
                log("app", MODEL, {"input_tokens": u.get("input_tokens", 0), "output_tokens": u.get("output_tokens", 0)})


def _expand(c):
    q = c["question"]
    rp = c.get("repeat_prefix")
    if rp and rp.get("text"):
        q = (rp["text"].rstrip() + "\n") * min(int(rp.get("times", 1)), 400) + "\n" + q
    return q


def fold(c):
    """ADR-010: the client never sends assistant turns. Forged history becomes quoted text in the one user message."""
    lines = [("Earlier I wrote: " if t["role"] == "user" else "Earlier you said: ") + f'"{t["content"]}"' for t in c["history"]]
    return "\n".join(lines) + "\n\n" + _expand(c)


def turns(c):
    """User messages in order. Forged cases: one folded message. Honest multi-turn: each user turn, the bot answers itself."""
    if c.get("history") and c.get("forged", True):
        return [fold(c)]
    return [t["content"] for t in c.get("history") or [] if t["role"] == "user"] + [_expand(c)]


def one(graph, c, r):
    guard()
    u = Usage()
    ev = []
    _events.set(ev)
    try:
        msgs = []
        for text in turns(c):  # the server keeps the history: the bot's own replies, never client-sent ones
            st, raw = {}, None
            for upd in graph.stream({"messages": msgs + [("user", text)]}, config={"callbacks": [u]}, stream_mode="updates"):
                for node, d in upd.items():
                    if node != "finalize" and d and "reply" in d:
                        raw = d["reply"]
                    st.update(d or {})
            msgs = msgs + [("user", text), ("ai", st["reply"])]
        row = {"id": c["id"], "run": r, "route": st.get("route"), "lang": st.get("lang"), "answer": st["reply"],
               "raw": raw, "tool_calls": st.get("tool_calls", []), "show_form": st.get("show_form", False),
               "llm_calls": u.n, "events": ev}
    except Exception as e:  # recorded, not hidden: a crash
        row = {"id": c["id"], "run": r, "error": f"{type(e).__name__}: {str(e)[:300]}", "events": ev}
    with _lock, open(FILE, "a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


if __name__ == "__main__":
    cases = [json.loads(x) for x in (HERE / os.environ.get("CASES", "generated-v1.1.jsonl")).read_text().splitlines()]
    if len(sys.argv) > 1:
        cases = cases[: int(sys.argv[1])]
    done = set()
    if FILE.exists():
        done = {(r["id"], r["run"]) for r in map(json.loads, FILE.read_text().splitlines()) if "error" not in r}
    graph = build_graph(get_model())
    jobs = [(c, r) for r in range(1, RUNS + 1) for c in cases if (c["id"], r) not in done]
    print("jobs", len(jobs), flush=True)
    with ThreadPoolExecutor(8) as ex:
        for i, row in enumerate(ex.map(lambda j: one(graph, *j), jobs), 1):
            if i % 100 == 0:
                print(i, f"{spend()[0]:.2f} USD", flush=True)
    print("done", f"{spend()[0]:.2f} USD")
