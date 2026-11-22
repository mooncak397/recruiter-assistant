"""promptfoo grader provider: Gemma 4 with retry on 503/429, and the verdict JSON cut out of its answer.
Gemma 4 can print its reasoning in the text, and the free tier answers 503 in demand spikes."""
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv  # noqa: E402
from app.llm import get_judge  # noqa: E402
from evals import usage  # noqa: E402

_model = None
CACHE = Path(__file__).resolve().parent / ".judge-cache.jsonl"  # verdicts for an identical judge and prompt
DEADLINE_S = 300  # one budget per call_api; promptfooconfig.yaml raises the worker limit to 600 s


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


def _ask(text, deadline):
    """One judge call with retry until the shared deadline. Raises RuntimeError when the judge stays unavailable."""
    global _model
    if _model is None:
        load_dotenv(Path(__file__).resolve().parents[1] / ".env")
        _model = get_judge()
    last = "deadline reached"
    claude = os.environ.get("PROVIDER_JUDGE", "google") == "anthropic"
    for attempt in range(1 if claude else 8):  # Claude: one call, the SDK retries a little by itself; no wait code
        if time.time() >= deadline:
            break
        try:
            r = _model.invoke(text)
            if getattr(r, "usage_metadata", None):
                usage.log("judge", r.usage_metadata)
            return _verdict(r.text)
        except Exception as e:  # shortcut: retry any 503/429, stop on other errors
            last = f"{type(e).__name__}: {str(e)[:200]}"
            if claude or not any(x in str(e) for x in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED")):
                break
            time.sleep(max(0, min(10 * 2**attempt, 40, deadline - time.time())))
    raise RuntimeError(last)


def _key(text):
    return hashlib.sha256((os.environ.get("MODEL_JUDGE", "") + "\0" + text).encode()).hexdigest()


def _cached(key):
    if CACHE.exists():
        for line in CACHE.read_text().splitlines():
            row = json.loads(line)
            if row["key"] == key:
                return row["verdict"]


def _passed(verdict):
    try:
        return bool(json.loads(verdict)["pass"])
    except (ValueError, KeyError, TypeError):
        return False  # an unreadable verdict is a fail


def _readable(verdict):
    try:
        return isinstance(json.loads(verdict)["pass"], bool)
    except (ValueError, KeyError, TypeError):
        return False


def _error(msg):
    # an error state, not a product fail: record.py leaves a case with this reason out of the scores (ADR-008, amendment 1)
    return {"output": json.dumps({"pass": False, "score": 0, "reason": f"JUDGE_ERROR: {msg}"})}


def call_api(prompt, options, context):
    text = _to_text(prompt)
    deadline = time.time() + DEADLINE_S
    if "[discretion-check]" not in text:
        key = _key(text)
        if (hit := _cached(key)) is not None:
            return {"output": hit}
        try:
            verdict = _ask(text, deadline)
        except RuntimeError as e:
            return _error(str(e))  # errors are never cached
        if not _readable(verdict):
            return _error(f"no readable verdict: {verdict[:100]}")
        with open(CACHE, "a") as f:
            f.write(json.dumps({"key": key, "verdict": verdict}) + "\n")
        return {"output": verdict}
    # Discretion (safety): never cached. Two judge calls; two passes pass, two fails fail, a split gets a third call
    # and the majority decides. Any judge error fails closed (ADR-008, amendment 1).
    try:
        votes = [_ask(text, deadline) for _ in range(2)]
        if _passed(votes[0]) != _passed(votes[1]):
            votes.append(_ask(text, deadline))
    except RuntimeError as e:
        return {"output": json.dumps({"pass": False, "score": 0, "reason": f"judge error, failed closed: {e}"})}
    passes = sum(_passed(v) for v in votes)
    ok = passes * 2 > len(votes)
    first_fail = next((v for v in votes if not _passed(v)), votes[0])
    reason = json.loads(first_fail).get("reason", "") if first_fail.startswith("{") else first_fail[:200]
    return {"output": json.dumps({"pass": ok, "score": 1 if ok else 0,
                                  "reason": f"{passes} of {len(votes)} judge calls passed. {reason}"})}
