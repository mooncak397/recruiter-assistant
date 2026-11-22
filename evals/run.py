"""Eval entry point (ADR-009).
  uv run python evals/run.py fast [--groups fact,unk] [--ids fact-en-01] [--failing old.json] [--changed <git-ref>] [--delay 3000]
      Code checks only, nothing recorded. With no selection: all golden cases. With a selection: the safety groups disc, inj, con plus the selection.
  uv run python evals/run.py version [--compare previous-official.json]   one full judged run and the official row
  uv run python evals/run.py release [--compare ...]                      3 judged runs, majority, one row (resumes: an existing run file is kept)
A daily-quota 429 (Gemini "PerDay") stops the run and prints the retry time. Run the same command again later:
finished cases come from evals/results/<run>.partial.jsonl and make no new app call."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

GROUPS = {"fact": "fact", "facts": "fact", "unk": "unk", "unknown": "unk", "disc": "disc", "discretion": "disc",
          "off": "off", "offtopic": "off", "inj": "inj", "injection": "inj", "con": "con", "contact": "con"}
SAFETY = ["disc", "inj", "con"]
OUT = ROOT / "evals/results"
STOP = OUT / ".quota-day"  # the same file as evals/provider.py STOP


def golden() -> dict[str, dict]:
    return {c["id"]: c for f in sorted((ROOT / "evals/golden").glob("*.yaml")) for c in yaml.safe_load(f.read_text())}


def changed_ids(ref: str) -> set[str]:
    """Golden cases that are new or different since a git ref."""
    now, old = golden(), {}
    for f in (ROOT / "evals/golden").glob("*.yaml"):
        shown = subprocess.run(["git", "show", f"{ref}:evals/golden/{f.name}"], cwd=ROOT, capture_output=True, text=True)
        if shown.returncode == 0:
            old.update({c["id"]: c for c in yaml.safe_load(shown.stdout)})
    return {i for i, c in now.items() if old.get(i) != c}


def claude() -> bool:
    """True when app and judge both run on Claude: no pacing, no waits (the paid key has no free-tier limits)."""
    return os.environ.get("PROVIDER_APP", "google") == "anthropic" and os.environ.get("PROVIDER_JUDGE", "google") == "anthropic"


def run_eval(out: Path, ids=None, judge=True, delay=None, replay_from=None):
    env = {**os.environ, "EVAL_JUDGE": "1" if judge else "0"}  # read by evals/tests.py
    cmd = ["npx", "promptfoo@0.126.0", "eval", "-c", "evals/promptfooconfig.yaml",  # no --env-file: it would override PROVIDER_* and MODEL_* ; the Python code reads .env itself
           "--no-cache", "-o", str(out)]
    if ids is not None:
        cmd += ["--filter-pattern", "^(" + "|".join(sorted(ids)) + ")$"]
    if claude():
        cmd += ["--delay", "0", "-j", "8"]
    elif delay:
        cmd += ["--delay", str(delay)]
    if replay_from:  # grade saved answers again, no app call
        env["REPLAY_FROM"] = str(replay_from)
        cmd += ["-r", "file://replay.py"]
    else:  # evals/provider.py saves each finished case here and replays it after a stop
        env["EVAL_PARTIAL"] = str(open_partial(out))
    out.parent.mkdir(exist_ok=True)
    out.unlink(missing_ok=True)
    STOP.unlink(missing_ok=True)
    subprocess.run(cmd, cwd=ROOT, env=env)  # promptfoo exits non-zero when a case fails: not an error here
    if STOP.exists():  # evals/provider.py hit the daily quota: this result file is incomplete
        out.unlink(missing_ok=True)
        sys.exit(f"Run stopped: {STOP.read_text().strip()}\n"
                 f"Run the same command again then: finished cases come from {partial_path(out).name}, no new calls.")
    if not out.exists():
        sys.exit(f"promptfoo wrote no result file: {out}")
    partial_path(out).unlink(missing_ok=True)  # the result file is complete


def partial_path(out: Path) -> Path:
    return out.with_name(out.stem + ".partial.jsonl")


def fingerprint() -> str:
    """Prompt, profile, app code and model: saved answers from other code must not be replayed."""
    h = hashlib.sha256()
    for f in [ROOT / "prompts/rules.md", ROOT / "profile/profile.md", *sorted((ROOT / "app").glob("*.py"))]:
        h.update(f.read_bytes())
    h.update((os.environ.get("PROVIDER_APP", "google") + os.environ.get("MODEL_APP", "")).encode())
    return h.hexdigest()[:16]


def open_partial(out: Path) -> Path:
    """Keep the per-case JSONL of a stopped run with the same fingerprint, else start a new one."""
    p, fp = partial_path(out), fingerprint()
    lines = p.read_text().splitlines() if p.exists() else []
    if lines and json.loads(lines[0]).get("fingerprint") == fp:
        print(f"resuming {out.name}: {len(lines) - 1} finished cases in {p.name}")
        return p
    if lines:
        print(f"{p.name} is from other code or another model: starting fresh")
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps({"fingerprint": fp}) + "\n")
    return p


def regrade_errors(out: Path, rounds: int = 2, pause: int | None = None):
    """Judge-error cases are graded again on the saved answer, after a pause, at most twice (ADR-008, amendment 1)."""
    from evals.record import is_error

    pause = (0 if claude() else 300) if pause is None else pause
    for _ in range(rounds):
        data = json.load(open(out))
        ids = [r["testCase"]["description"] for r in data["results"]["results"] if is_error(r)]
        if not ids:
            return
        print(f"{len(ids)} judge errors, waiting {pause} s: {' '.join(ids)}")
        if pause:
            time.sleep(pause)
        tmp = out.with_suffix(".regrade.json")
        run_eval(tmp, ids, judge=True, replay_from=out)
        new = {r["testCase"]["description"]: r for r in json.load(open(tmp))["results"]["results"]}
        data["results"]["results"] = [new.get(r["testCase"]["description"], r) for r in data["results"]["results"]]
        json.dump(data, open(out, "w"))
        tmp.unlink()


PRICES = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.0, 10.0)}  # USD per 1M tokens (input, output)


def cost_report() -> str:
    """Tokens and USD for the Claude calls logged since the last reset (evals/.usage.jsonl)."""
    from evals.usage import LOG

    rows = [json.loads(l) for l in LOG.read_text().splitlines()] if LOG.exists() else []
    parts, total = [], 0.0
    for role in ("app", "judge"):
        r = [x for x in rows if x["role"] == role]
        if r:
            pin, pout = PRICES.get(r[0]["model"], (0, 0))
            usd = sum(x["in"] for x in r) / 1e6 * pin + sum(x["out"] for x in r) / 1e6 * pout
            total += usd
            parts.append(f"{role}: {len(r)} calls, {sum(x['in'] for x in r)} in / {sum(x['out'] for x in r)} out tokens, ${usd:.3f}")
    return " | ".join(parts) + f" | total ${total:.3f}" if parts else "no usage logged"


def summary(out: Path, seconds: float):
    rs = json.load(open(out))["results"]["results"]
    meta = [r["response"].get("metadata") or {} for r in rs]
    bad = [r["testCase"]["description"] for r in rs if not r["success"]]
    print(f"{len(rs)} cases, {len(rs) - len(bad)} pass, {seconds:.0f} s, app calls {sum(m.get('llm_calls', 0) for m in meta)}, "
          f"rate_limited {sum(m.get('rate_limited', 0) for m in meta)}")
    print("failing:", " ".join(bad) or "none")
    print(calls_per_case(rs))
    print("usage:", cost_report())


FREE_PER_DAY = 500  # gemini-3.5-flash-lite free tier: requests per day


def calls_per_case(rs: list[dict]) -> str:
    """App calls per case (classify + answer + tool), to plan a run against the free daily quota."""
    n = [(r["response"].get("metadata") or {}).get("llm_calls", 0) for r in rs]
    avg = sum(n) / len(n) if n else 0
    if not avg:
        return "app calls per case: none logged"
    i = max(range(len(n)), key=n.__getitem__)
    return (f"app calls per case: avg {avg:.1f}, max {n[i]} ({rs[i]['testCase']['description']}); "
            f"{FREE_PER_DAY} requests/day = about {int(FREE_PER_DAY // avg)} cases")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    f = sub.add_parser("fast")
    f.add_argument("--groups", default="")
    f.add_argument("--ids", default="")
    f.add_argument("--failing")
    f.add_argument("--changed")
    f.add_argument("--delay", type=int, default=3000)
    for m in ("version", "release"):
        sub.add_parser(m).add_argument("--compare")
    a = ap.parse_args(argv)

    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")  # MODEL_APP and MODEL_JUDGE for the row
    cases = golden()
    from evals.usage import LOG

    LOG.unlink(missing_ok=True)  # the cost report covers this command only
    if a.mode == "fast":
        wanted = {GROUPS[g] for g in a.groups.split(",") if g}
        ids = {i for i in cases if i.split("-")[0] in wanted} | {i for i in a.ids.split(",") if i}
        if a.failing:
            ids |= {r["testCase"]["description"] for r in json.load(open(a.failing))["results"]["results"] if not r["success"]}
        if a.changed:
            ids |= changed_ids(a.changed)
        # no selection = all golden cases; a selection always carries the safety groups (ADR-009)
        selected = bool(a.groups or a.ids or a.failing or a.changed)
        ids = ids | {i for i in cases if i.split("-")[0] in SAFETY} if selected else set(cases)
        unknown = ids - set(cases)
        if unknown:
            sys.exit(f"unknown case ids: {sorted(unknown)}")
        out, t0 = OUT / "fast-latest.json", time.time()
        run_eval(out, ids, judge=False, delay=a.delay)
        summary(out, time.time() - t0)
        return
    from evals import record

    from app.prompts import rules_version

    ver = rules_version()
    outs = [OUT / (f"{ver}.json" if a.mode == "version" else f"{ver}-run{i}.json") for i in ([1] if a.mode == "version" else [1, 2, 3])]
    for out in outs:
        if a.mode == "release" and out.exists():
            print(f"keeping {out.name} (resume)")
            continue
        t0 = time.time()
        run_eval(out)
        regrade_errors(out)
        summary(out, time.time() - t0)
    record.main([str(o) for o in outs], a.compare)


if __name__ == "__main__":
    main()
