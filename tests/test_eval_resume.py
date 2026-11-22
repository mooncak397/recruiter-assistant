"""Eval runner gaps from the Gemini run: client timeout, daily-quota stop, per-case partial results and resume.
No key, no network: the graph and promptfoo are faked."""
import json
import logging

import pytest
from langchain_core.messages import AIMessage

from app.texts import BUSY
from evals import provider, run

STATE = {"route": "cv_question", "lang": "en", "tool_calls": [], "show_form": False}


class FakeGraph:
    """Returns one reply; can log a model error the way app/graph.py's _call does."""

    def __init__(self, reply="He works at DATEV.", error=None):
        self.reply, self.error, self.calls = reply, error, 0

    def invoke(self, _input, config=None):
        self.calls += 1
        if self.error is not None:
            logging.getLogger("app.graph").warning("model_error", extra={"error": self.error})
        return {**STATE, "messages": [AIMessage(self.reply)]}


@pytest.fixture
def fresh(tmp_path, monkeypatch):
    monkeypatch.setattr(provider, "STOP", tmp_path / ".quota-day")
    monkeypatch.setattr(provider, "_done", None)
    monkeypatch.setenv("EVAL_PARTIAL", str(tmp_path / "v1.partial.jsonl"))
    return tmp_path


def test_daily_quota_stops_at_once_and_marks_the_case(fresh, monkeypatch):
    monkeypatch.setenv("PROVIDER_APP", "google")
    g = FakeGraph(reply=BUSY["en"], error=RuntimeError("429 RESOURCE_EXHAUSTED GenerateRequestsPerDayPerProjectPerModel"))
    monkeypatch.setattr(provider, "_graph", g)
    out = provider.call_api("Where does he work?", {}, {})
    assert out["error"].startswith("quota-day") and g.calls == 1  # no retry
    assert provider.STOP.exists() and "retry after" in provider.STOP.read_text()
    assert provider.call_api("Next question?", {}, {})["error"].startswith("quota-day") and g.calls == 1


def test_finished_cases_are_saved_and_replayed_on_resume(fresh, monkeypatch):
    g = FakeGraph()
    monkeypatch.setattr(provider, "_graph", g)
    first = provider.call_api("Where does he work?", {}, {})
    row = json.loads((fresh / "v1.partial.jsonl").read_text().splitlines()[-1])
    assert row["prompt"] == "Where does he work?" and row["metadata"]["llm_calls"] == 0  # FakeGraph fires no callback
    monkeypatch.setattr(provider, "_done", None)  # a new process after a stop
    again = provider.call_api("Where does he work?", {}, {})
    assert again["output"] == first["output"] and again["metadata"]["resumed"] and g.calls == 1


def test_run_eval_stops_on_the_quota_marker_and_keeps_the_partial_file(tmp_path, monkeypatch):
    out = tmp_path / "v1-run1.json"
    monkeypatch.setattr(run, "STOP", tmp_path / ".quota-day")
    monkeypatch.setattr(provider, "STOP", tmp_path / ".quota-day")

    def fake_promptfoo(cmd, cwd, env):
        out.write_text("{}")
        open(env["EVAL_PARTIAL"], "a").write(json.dumps({"prompt": "q", "output": "{}", "metadata": {}}) + "\n")
        run.STOP.write_text("quota-day hit; retry after 2026-11-23 09:00")

    monkeypatch.setattr(run.subprocess, "run", fake_promptfoo)
    with pytest.raises(SystemExit, match="retry after 2026-11-23 09:00"):
        run.run_eval(out)
    assert not out.exists()  # a stopped run file must not count as finished (release resume keeps run files)
    assert run.partial_path(out).exists()


def test_partial_file_from_other_code_is_dropped(tmp_path, monkeypatch):
    out = tmp_path / "v1.json"
    p = run.partial_path(out)
    p.write_text(json.dumps({"fingerprint": "old"}) + "\n" + json.dumps({"prompt": "q", "output": "{}"}) + "\n")
    run.open_partial(out)
    assert p.read_text().splitlines() == [json.dumps({"fingerprint": run.fingerprint()})]
    p.write_text(p.read_text() + json.dumps({"prompt": "q", "output": "{}"}) + "\n")
    run.open_partial(out)  # same code: keep the finished cases
    assert len(p.read_text().splitlines()) == 2


def test_gemini_client_has_a_timeout(monkeypatch):
    from app import llm

    seen = {}
    monkeypatch.setattr(llm, "load_dotenv", lambda: None)
    monkeypatch.setattr(llm, "init_chat_model", lambda name, **k: seen.update(k))
    monkeypatch.setenv("MODEL_APP", "gemini-x")
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    monkeypatch.delenv("PROVIDER_APP", raising=False)
    llm.get_model()
    assert seen["timeout"] == 60


def test_calls_per_case_line():
    rs = [{"testCase": {"description": f"c{i}"}, "response": {"metadata": {"llm_calls": n}}} for i, n in enumerate([2, 2, 3, 1])]
    assert run.calls_per_case(rs) == "app calls per case: avg 2.0, max 3 (c2); 500 requests/day = about 250 cases"
