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


def call_api(prompt, options, context):
    global _model
    if _model is None:
        load_dotenv(Path(__file__).resolve().parents[1] / ".env")
        _model = init_chat_model(os.environ["MODEL_JUDGE"], model_provider="google_genai", temperature=0)
    last, start = "", time.time()
    for attempt in range(8):
        if time.time() - start > 150:  # promptfoo kills a Python worker after 300 s
            break
        try:
            return {"output": _verdict(_model.invoke(_to_text(prompt)).text)}
        except Exception as e:  # shortcut: retry any 503/429, return other errors
            last = f"{type(e).__name__}: {str(e)[:200]}"
            if not any(x in str(e) for x in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED")):
                break
            time.sleep(min(10 * 2**attempt, 40))
    return {"error": last}
