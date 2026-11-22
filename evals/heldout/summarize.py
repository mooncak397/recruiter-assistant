"""Step 3/4 helper: aggregates out/grades.jsonl -> out/summary.json, out/failures.jsonl, out/judge-sample.jsonl."""
import collections
import json
import os
import random
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from common import HERE, OUT, USAGE, cost_row  # noqa: E402

cases = {c["id"]: c for c in map(json.loads, (HERE / os.environ.get("CASES", "generated-v1.1.jsonl")).read_text().splitlines())}
runs = {(r["id"], r["run"]): r for r in map(json.loads, (OUT / "runs.jsonl").read_text().splitlines()) if "error" not in r}
grades = {(g["id"], g["run"]): g for g in map(json.loads, (OUT / "grades.jsonl").read_text().splitlines())}
S = {"groups": {}, "errors": sum(1 for g in grades.values() if "error" in g)}
fails = []
for grp in ("disc", "inj", "fact", "unk", "con"):
    gs = [g for g in grades.values() if g.get("group") == grp]
    ids = {g["id"] for g in gs}
    case_fail = {i for i in ids if any(not g["pass"] for g in gs if g["id"] == i)}
    tags = collections.Counter()
    for g in gs:
        for t in g["code"]:
            tags[t.split(":")[0] if not t.startswith("tool") else "tool"] += 1
        for k, v in g["judge"].items():
            if not v["pass"]:
                tags["judge_" + k] += 1
        for t in g["soft"]:
            tags["soft_route"] += 1
    S["groups"][grp] = {"runs": len(gs), "run_pass": sum(g["pass"] for g in gs), "cases": len(ids),
                        "cases_fail_any_run": len(case_fail), "tags": dict(tags.most_common())}
for k, g in grades.items():
    if "error" in g or g["pass"]:
        continue
    c, r = cases[g["id"]], runs[k]
    fails.append({"id": g["id"], "run": g["run"], "lang": c["lang"], "sub": c.get("subtype"), "q": c["question"][-300:],
                  "hist": bool(c.get("history")), "exp": c.get("expected"), "fixed": c.get("expect_fixed"),
                  "a": r["answer"][:500], "route": r["route"], "tools": r["tool_calls"], "code": g["code"],
                  "judge": {kk: v.get("reason", "")[:200] for kk, v in g["judge"].items() if not v["pass"]}})
(OUT / "failures.jsonl").write_text("".join(json.dumps(f, ensure_ascii=False) + "\n" for f in sorted(fails, key=lambda f: (f["id"], f["run"]))))
judged = [(k, m, v) for k, g in grades.items() if "judge" in g for m, v in g["judge"].items()]
random.Random(20261122).shuffle(judged)
sample = [{"n": i + 1, "id": k[0], "run": k[1], "metric": m, "verdict": v["pass"], "reason": v.get("reason", "")[:250],
           "q": cases[k[0]]["question"][-250:], "exp": cases[k[0]].get("expected"), "facts": cases[k[0]].get("key_facts"),
           "a": runs[k]["answer"][:700]} for i, (k, m, v) in enumerate(judged[:30])]
(OUT / "judge-sample.jsonl").write_text("".join(json.dumps(s, ensure_ascii=False) + "\n" for s in sample))
rows = [json.loads(x) for x in USAGE.read_text().splitlines()]
by = collections.defaultdict(lambda: [0, 0.0])
for r in rows:
    by[f"{r['role']}/{r['model']}"][0] += 1
    by[f"{r['role']}/{r['model']}"][1] += cost_row(r)
S["spend"] = {k: [n, round(u, 2)] for k, (n, u) in by.items()}
S["spend_total"] = round(sum(u for _, u in by.values()), 2)
S["judged_verdicts"] = len(judged)
(OUT / "summary.json").write_text(json.dumps(S, indent=1))
print(json.dumps(S))
