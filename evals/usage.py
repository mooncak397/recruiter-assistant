"""Token usage log for the cost report (evals/.usage.jsonl, not committed)."""
import json
import os
from pathlib import Path

LOG = Path(__file__).resolve().parent / ".usage.jsonl"


def log(role: str, u: dict):
    model = os.environ.get("MODEL_APP" if role == "app" else "MODEL_JUDGE", "")
    with open(LOG, "a") as f:
        f.write(json.dumps({"role": role, "model": model, "in": u.get("input_tokens", 0), "out": u.get("output_tokens", 0)}) + "\n")
