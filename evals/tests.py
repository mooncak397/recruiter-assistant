"""promptfoo test generator: golden YAML -> promptfoo tests. The shorthand asserts stay in the YAML."""
import json
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROFILE = (ROOT / "profile/profile.md").read_text()

FACTUAL = ("Reference answer: {ref}\nIs every claim in the answer consistent with the reference, "
           "and are the key facts of the reference present? Pass only if yes.")
INVENTION = ("Here is the profile of Christopher:\n---\n{profile}\n---\nDoes the answer state anything about "
             "Christopher that is not in this profile? Pass only if it does NOT.")
TONE = "Is the answer polite, professional, written about Christopher in the third person, and free of sales talk? Pass only if yes."


def _rubric(metric, text):
    # grade only the answer text, not the whole JSON
    return {"type": "llm-rubric", "metric": metric, "transform": "JSON.parse(output).answer", "value": text}


def generate_tests(config=None):
    tests = []
    for f in sorted((HERE / "golden").glob("*.yaml")):
        for c in yaml.safe_load(f.read_text()):
            gid = c["id"].split("-")[0]
            asserts = [{"type": "python", "value": "file://asserts/check.py"}]
            ref = c.get("reference_en") or c["expected"]
            if gid == "fact":
                asserts += [_rubric("factual", FACTUAL.format(ref=ref)),
                            _rubric("invention", INVENTION.format(profile=PROFILE))]
            if c["id"] in ("disc-en-03", "disc-de-03"):
                asserts.append(_rubric("tone_judge", TONE))
            tests.append({
                "description": c["id"],
                "vars": {"message": c["vars"]["message"], "id": c["id"], "lang": c["lang"],
                         "route": json.dumps(c["route"]),  # a string: promptfoo expands a list var into several tests
                         "checks": c["assert"]},
                "assert": asserts,
            })
    return tests
