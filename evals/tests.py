"""promptfoo test generator: golden YAML -> promptfoo tests. The shorthand asserts stay in the YAML."""
import json
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROFILE = (ROOT / "profile/profile.md").read_text()

FACTUAL = ("Reference answer: {ref}\nFacts the answer must contain:\n{facts}\n"
           "Pass only if no claim in the answer contradicts the reference AND every listed fact is in the answer. "
           "Other details of the reference may be missing. Extra true details are not a contradiction "
           "(a separate check looks for invented facts). The answer may be in German.")
INVENTION = ("Here is the profile of Christopher:\n---\n{profile}\n---\nDoes the answer state anything about "
             "Christopher that is not in this profile? Inferences and labels count as invention: an opinion, a feeling "
             "or a size that the profile does not state (for example 'comfortable', 'production-style', 'expert', "
             "'commercial') is invention, even when it sounds reasonable. Pass only if the answer has none.")
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
                asserts += [_rubric("factual", FACTUAL.format(ref=ref, facts="\n".join("- " + f for f in c["must_include"]))),
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
