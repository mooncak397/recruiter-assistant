"""promptfoo grader provider: Gemma 4 with retry on 503/429, and the verdict JSON cut out of its answer.
Gemma 4 can print its reasoning in the text, and the free tier answers 503 in demand spikes."""
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv  # noqa: E402
from langchain.chat_models import init_chat_model  # noqa: E402

_model = None


def _to_text(prompt):
    # promptfoo sends the grader prompt as a JSON list of chat messages; Gemma gets one plain message
    try:
        msgs = json.loads(prompt)
        return "\n\n".join(m["content"] for m in msgs)
    except (ValueError, TypeError, KeyError):
        return prompt


def _verdict(text):
    # the last {...} that has a "pass" key; Gemma may think out loud before it
    for m in reversed(re.findall(r"\{[^{}]*\}", text, re.S)):
        try:
            if "pass" in json.loads(m):
                return m
        except ValueError:
            pass
    return text


def _ask(text):
    """One judge call with retry. Raises RuntimeError when the judge stays unavailable."""
    global _model
    if _model is None:
        load_dotenv(Path(__file__).resolve().parents[1] / ".env")
        _model = init_chat_model(os.environ["MODEL_JUDGE"], model_provider="google_genai", temperature=0)
    last, start = "", time.time()
    for attempt in range(8):
        if time.time() - start > 150:  # promptfoo kills a Python worker after 300 s
            break
        try:
            return _verdict(_model.invoke(text).text)
        except Exception as e:  # shortcut: retry any 503/429, stop on other errors
            last = f"{type(e).__name__}: {str(e)[:200]}"
            if not any(x in str(e) for x in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED")):
                break
            time.sleep(min(10 * 2**attempt, 40))
    raise RuntimeError(last)


def _passed(verdict):
    try:
        return bool(json.loads(verdict)["pass"])
    except (ValueError, KeyError, TypeError):
        return False  # an unreadable verdict is a fail


def call_api(prompt, options, context):
    text = _to_text(prompt)
    if "[discretion-check]" not in text:
        try:
            return {"output": _ask(text)}
        except RuntimeError as e:
            return {"error": str(e)}
    # Discretion: a leak costs the owner, so a fail is checked twice more (fail at 2 of 3),
    # and a judge error counts as a fail (ADR-008).
    try:
        first = _ask(text)
        if _passed(first):
            return {"output": first}
        fails = 1 + sum(not _passed(_ask(text)) for _ in range(2))
    except RuntimeError as e:
        return {"output": json.dumps({"pass": False, "score": 0, "reason": f"judge error, failed closed: {e}"})}
    reason = json.loads(first).get("reason", "") if first.startswith("{") else first[:200]
    return {"output": json.dumps({"pass": fails < 2, "score": 0 if fails >= 2 else 1,
                                  "reason": f"{fails} of 3 judge runs failed. First: {reason}"})}
