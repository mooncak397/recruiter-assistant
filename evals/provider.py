"""promptfoo Python provider: runs the real graph and returns JSON (plan section 7)."""
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.callbacks import BaseCallbackHandler  # noqa: E402

from app.graph import build_graph  # noqa: E402
from app.llm import get_model  # noqa: E402
from app.texts import BUSY  # noqa: E402
from evals import usage  # noqa: E402

_graph = None
_done = None  # prompt -> saved result, loaded once per worker
STOP = Path(__file__).resolve().parent / "results/.quota-day"  # written on a daily-quota 429; run.py stops the run


class CountCalls(BaseCallbackHandler):
    def __init__(self):
        self.n = 0

    def on_chat_model_start(self, *a, **k):
        self.n += 1

    def on_llm_end(self, response, **k):  # token counts for the cost report
        for g in response.generations:
            u = getattr(g[0].message, "usage_metadata", None) if g else None
            if u:
                usage.log("app", u)


class ModelErrors(logging.Handler):
    """Collects the exceptions that app/graph.py's _call caught and logged."""

    def __init__(self):
        super().__init__()
        self.errors = []

    def emit(self, record):
        if getattr(record, "error", None) is not None:
            self.errors.append(record.error)


def _quota_reset() -> str:
    """Gemini daily quotas reset at midnight Pacific time; shown in local time."""
    pt = datetime.now(ZoneInfo("America/Los_Angeles"))
    reset = (pt + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return reset.astimezone().strftime("%Y-%m-%d %H:%M %Z")


def _saved() -> dict:
    """Finished cases of a stopped run (EVAL_PARTIAL, set by run.py), keyed by the message."""
    global _done
    if _done is None:
        p = os.environ.get("EVAL_PARTIAL")
        rows = [json.loads(line) for line in open(p)] if p and Path(p).exists() else []
        _done = {r["prompt"]: r for r in rows if "prompt" in r}
    return _done


def _save(prompt, result: dict) -> dict:
    if p := os.environ.get("EVAL_PARTIAL"):
        with open(p, "a") as f:  # one short line per case: appends from parallel workers do not mix
            f.write(json.dumps({"prompt": prompt, **result}, ensure_ascii=False) + "\n")
    return result


def call_api(prompt, options, context):
    global _graph
    if STOP.exists():  # the daily quota is gone: no more calls in this run
        return {"error": "quota-day: run stopped"}
    if prompt in _saved():  # resume: this case finished before the stop
        r = _saved()[prompt]
        return {"output": r["output"], "metadata": {**r.get("metadata", {}), "resumed": True}}
    _graph = _graph or build_graph(get_model())
    waits = 0
    graph_log = logging.getLogger("app.graph")
    for attempt in range(6):
        counter, errors = CountCalls(), ModelErrors()
        graph_log.addHandler(errors)
        try:
            s = _graph.invoke({"messages": [("user", prompt)]}, config={"callbacks": [counter]})
            if any("PerDay" in str(e) for e in errors.errors):  # retrying a daily quota only burns time
                STOP.parent.mkdir(exist_ok=True)
                STOP.write_text(f"quota-day hit at {datetime.now():%Y-%m-%d %H:%M}; retry after {_quota_reset()}\n")
                return {"error": "quota-day: daily request limit reached", "metadata": {"llm_calls": counter.n}}
            if s["messages"][-1].text not in BUSY.values():
                break
            # the graph turns 429/5xx into the BUSY text (ADR-010); for the eval that is an error, not an answer
            raise RuntimeError("429 busy reply from the graph")
        except Exception as e:  # shortcut: any 429-like error is retried, others returned as errors
            # Gemini free tier: wait and retry. Claude: the SDK retries a little by itself, no wait code here.
            if os.environ.get("PROVIDER_APP", "google") == "google" and ("429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)):
                waits += 1
                time.sleep(min(15 * 2**attempt, 90))
                continue
            return {"error": f"{type(e).__name__}: {str(e)[:300]}"}
        finally:
            graph_log.removeHandler(errors)
    else:
        return {"error": "rate limited after 6 tries"}
    out = {"route": s["route"], "lang": s["lang"], "answer": s["messages"][-1].text,
           "tool_calls": s["tool_calls"], "show_form": s["show_form"]}
    return _save(prompt, {"output": json.dumps(out, ensure_ascii=False),
                          "metadata": {"llm_calls": counter.n, "rate_limited": waits}})
