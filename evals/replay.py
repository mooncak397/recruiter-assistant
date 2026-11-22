"""Provider that replays the saved answers of an earlier run (env REPLAY_FROM), so only the grading runs again.
No app model call is made."""
import json
import os


def call_api(prompt, options, context):
    saved = json.load(open(os.environ["REPLAY_FROM"]))["results"]["results"]
    by_id = {r["testCase"]["description"]: r["response"]["output"] for r in saved}
    return {"output": by_id[context["vars"]["id"]]}
