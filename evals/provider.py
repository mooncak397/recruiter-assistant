"""promptfoo Python provider: runs the real graph and returns JSON (plan section 7)."""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.callbacks import BaseCallbackHandler  # noqa: E402

from app.graph import build_graph  # noqa: E402
from app.llm import get_model  # noqa: E402
from evals import usage  # noqa: E402

_graph = None


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


def call_api(prompt, options, context):
    global _graph
    _graph = _graph or build_graph(get_model())
    waits = 0
    for attempt in range(6):
        counter = CountCalls()
        try:
            s = _graph.invoke({"messages": [("user", prompt)]}, config={"callbacks": [counter]})
            break
        except Exception as e:  # shortcut: any 429-like error is retried, others returned as errors
            # Gemini free tier: wait and retry. Claude: the SDK retries a little by itself, no wait code here.
            if os.environ.get("PROVIDER_APP", "google") == "google" and ("429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)):
                waits += 1
                time.sleep(min(15 * 2**attempt, 90))
                continue
            return {"error": f"{type(e).__name__}: {str(e)[:300]}"}
    else:
        return {"error": "rate limited after 6 tries"}
    out = {"route": s["route"], "lang": s["lang"], "answer": s["messages"][-1].text,
           "tool_calls": s["tool_calls"], "show_form": s["show_form"]}
    return {"output": json.dumps(out, ensure_ascii=False),
            "metadata": {"llm_calls": counter.n, "rate_limited": waits}}
