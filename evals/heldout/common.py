"""Shared bits for the held-out red-team run: Claude client, usage log, cost, budget guard."""
import json
import os
import threading
from pathlib import Path

import anthropic
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE / os.environ.get("OUT_DIR", "out")
OUT.mkdir(parents=True, exist_ok=True)
USAGE = OUT / "usage.jsonl"
PRICES = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.0, 10.0), "claude-opus-5-5": (4.0, 20.0)}  # USD / 1M (in, out)
CACHE_READ = {"claude-haiku-5-5": 0.01, "claude-sonnet-5-5": 0.10, "claude-opus-5-5": 0.20}
STOP_USD = float(os.environ.get("STOP_USD", "100"))
_lock = threading.Lock()
load_dotenv(ROOT / ".env")
client = anthropic.Anthropic(max_retries=6)


def cost_row(r):
    pi, po = PRICES[r["model"]]
    cw = r.get("cache_write", 0) * pi * 1.25
    cr = r.get("cache_read", 0) * CACHE_READ[r["model"]]
    return (r["in"] * pi + r["out"] * po + cw + cr) / 1e6


def log(role, model, u):
    row = {"role": role, "model": model, "in": u.get("input_tokens", 0) or 0, "out": u.get("output_tokens", 0) or 0,
           "cache_write": u.get("cache_creation_input_tokens", 0) or 0, "cache_read": u.get("cache_read_input_tokens", 0) or 0}
    with _lock, open(USAGE, "a") as f:
        f.write(json.dumps(row) + "\n")


def spend():
    if not USAGE.exists():
        return 0.0, 0
    rows = [json.loads(x) for x in USAGE.read_text().splitlines()]
    return sum(cost_row(r) for r in rows), len(rows)


def guard():
    usd, _ = spend()
    if usd >= STOP_USD:
        raise SystemExit(f"budget stop: {usd:.2f} USD spent")


def ask(model, system, user, role, max_tokens=16000, effort=None, cache_system=True):
    guard()
    kw = {"output_config": {"effort": effort}} if effort else {}
    sys_block = [{"type": "text", "text": system, **({"cache_control": {"type": "ephemeral"}} if cache_system else {})}]
    with client.messages.stream(model=model, max_tokens=max_tokens, system=sys_block,
                                messages=[{"role": "user", "content": user}], **kw) as s:
        m = s.get_final_message()
    log(role, model, m.usage.model_dump())
    return "".join(b.text for b in m.content if b.type == "text"), m.stop_reason
