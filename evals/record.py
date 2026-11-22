"""promptfoo results JSON -> one row in evals/history.csv, and a per-group table on stdout.
Usage: uv run python evals/record.py run1.json [run2.json run3.json]
(The README chart block is M10.)"""
import csv
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "evals/history.csv"
COLUMNS = ["date", "prompt_version", "golden_version", "git_sha", "model_app", "model_judge", "n", "route", "lang",
           "facts", "no_invention", "injection", "tool_precision", "tool_recall", "tone", "overall",
           "discretion", "de_pass", "app_calls", "length", "runs", "unstable"]


def majority(runs: list[list[dict]]) -> tuple[list[dict], int]:
    """Several runs of the same cases -> one result per case (2 of 3 decide) and the number of unstable cases."""
    by_case: dict[str, list[dict]] = {}
    for run in runs:
        for r in run:
            by_case.setdefault(r["testCase"]["description"], []).append(r)
    chosen, unstable = [], 0
    for rs in by_case.values():
        wins = sum(r["success"] for r in rs) * 2 > len(rs)
        chosen.append(next(r for r in rs if r["success"] == wins))  # an entry that matches the majority verdict
        unstable += len({r["success"] for r in rs}) > 1
    return chosen, unstable


def metrics(results: list[dict]) -> dict:
    """results = promptfoo result entries. Percent values are over all matching cases (n = 53)."""
    cases = [(r["testCase"]["description"], r["namedScores"], r["success"], r) for r in results]
    pct = lambda xs: round(100 * sum(xs) / len(xs), 1) if xs else None
    grp = lambda g: [c for c in cases if c[0].startswith(g + "-")]
    called = sum(s["called"] for _, s, _, _ in cases)
    want = sum(s["want_call"] for _, s, _, _ in cases)
    hit = sum(s["called"] and s["want_call"] for _, s, _, _ in cases)
    de = [c for c in cases if "-de-" in c[0]]
    inv = [s["content"] for _, s, _, _ in grp("unk")] + [s["invention"] for _, s, _, _ in grp("fact")]
    return {
        "n": len(cases),
        "route": pct([s["route"] for _, s, _, _ in cases]),
        "lang": pct([s["lang"] for _, s, _, _ in cases]),
        "facts": pct([s["content"] and s["factual"] for _, s, _, _ in grp("fact")]),
        "no_invention": pct(inv),
        "injection": pct([ok for _, _, ok, _ in grp("inj")]),
        "tool_precision": pct([1] * hit + [0] * (called - hit)),
        "tool_recall": pct([1] * hit + [0] * (want - hit)),
        "tone": pct([s["tone_code"] and s.get("tone_judge", 1) for _, s, _, _ in cases]),
        "overall": pct([ok for _, _, ok, _ in cases]),
        "discretion": pct([ok for _, _, ok, _ in grp("disc")]),
        "de_pass": f"{sum(ok for _, _, ok, _ in de)}/{len(de)}",  # a count, never a percentage
        "length": pct([s["length"] for _, s, _, _ in cases]),
        "app_calls": sum((r["response"].get("metadata") or {}).get("llm_calls", 0) for _, _, _, r in cases),
    }


def group_table(results: list[dict]) -> str:
    lines = []
    for g in ("fact", "unk", "disc", "off", "inj", "con"):
        c = [r for r in results if r["testCase"]["description"].startswith(g + "-")]
        de = [r for r in c if "-de-" in r["testCase"]["description"]]
        lines.append(f"{g}: {sum(r['success'] for r in c)}/{len(c)} (DE {sum(r['success'] for r in de)}/{len(de)})")
    return "\n".join(lines)


def main(paths: list[str]):
    runs = [json.load(open(p))["results"]["results"] for p in paths]
    results, unstable = majority(runs)
    rules = (ROOT / "prompts/rules.md").read_text()
    row = {
        "date": date.today().isoformat(),
        "prompt_version": re.match(r"version: (v\d+)", rules).group(1),
        "golden_version": "golden-v1",
        "git_sha": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip(),
        "model_app": os.environ.get("MODEL_APP", ""),
        "model_judge": os.environ.get("MODEL_JUDGE", ""),
        **metrics(results),
        "runs": len(runs),
        "unstable": unstable,
    }
    old = list(csv.DictReader(open(HISTORY))) if HISTORY.exists() else []  # keep old rows, new columns stay empty
    with open(HISTORY, "w", newline="") as f:
        w = csv.DictWriter(f, COLUMNS)
        w.writeheader()
        w.writerows(old + [row])
    print(group_table(results))
    print(row)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    main(sys.argv[1:])  # one file per run; three files = a release (majority)
