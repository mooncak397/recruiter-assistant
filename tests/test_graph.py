"""Router tests: no key, no network. FakeModel stands in for Gemini."""
import pytest
from langchain_core.messages import AIMessage, SystemMessage

from app.cli import ask
from app.graph import Classification, build_graph
from app.texts import FORM_INTRO, OFF_TOPIC


class FakeModel:
    """Scripted answers; records every call so tests can see which node used the LLM."""

    def __init__(self, route="cv_question", lang="en", reply=None):
        self.cls = Classification(route=route, lang=lang)
        self.reply = reply or AIMessage("He works at DATEV.")
        self.calls = []  # (kind, messages)

    def with_structured_output(self, _schema):
        return _Step(self, "classify", self.cls)

    def bind_tools(self, tools):
        assert [t.name for t in tools] == ["request_contact_form"]  # exactly one tool
        return _Step(self, "contact", self.reply)

    def invoke(self, messages):
        self.calls.append(("answer", messages))
        return self.reply


class _Step:
    def __init__(self, parent, kind, out):
        self.parent, self.kind, self.out = parent, kind, out

    def invoke(self, messages):
        self.parent.calls.append((self.kind, messages))
        return self.out


def kinds(m):
    return [k for k, _ in m.calls]


def test_cv_question_uses_rules_and_profile():
    m = FakeModel()
    s = ask(build_graph(m), "Where does Christopher work?")
    assert s["messages"][-1].text == "He works at DATEV."
    assert kinds(m) == ["classify", "answer"]
    system = m.calls[1][1][0]
    assert isinstance(system, SystemMessage) and "version: v" in system.content and "DATEV" in system.content
    assert not s["show_form"] and s["tool_calls"] == []


@pytest.mark.parametrize("lang", ["en", "de"])
def test_off_topic_is_fixed_text_and_costs_one_call(lang):
    m = FakeModel(route="off_topic", lang=lang)
    s = ask(build_graph(m), "What is the weather?")
    assert s["messages"][-1].text == OFF_TOPIC[lang]
    assert kinds(m) == ["classify"]  # no LLM call for the answer


@pytest.mark.parametrize("lang", ["en", "de"])
def test_contact_tool_call_opens_form_with_fixed_text(lang):
    reply = AIMessage("", tool_calls=[{"name": "request_contact_form", "args": {}, "id": "1"}])
    s = ask(build_graph(FakeModel(route="contact", lang=lang, reply=reply)), "I'd like to talk to him")
    assert s["show_form"] is True and s["tool_calls"] == ["request_contact_form"]
    assert s["messages"][-1].text == FORM_INTRO[lang]


def test_contact_unclear_asks_and_shows_no_form():
    s = ask(build_graph(FakeModel(route="contact", reply=AIMessage("What would you like to discuss?"))), "contact?")
    assert s["show_form"] is False and s["tool_calls"] == []
    assert s["messages"][-1].text == "What would you like to discuss?"


def test_fixed_texts_follow_swiss_spelling():
    assert all("ß" not in t for t in [*OFF_TOPIC.values(), *FORM_INTRO.values()])


def test_get_model_fails_clearly_without_settings(monkeypatch):
    from app import llm

    monkeypatch.setattr(llm, "load_dotenv", lambda: None)  # ignore a real .env
    for v in ("MODEL_APP", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(v, raising=False)
    with pytest.raises(SystemExit, match="MODEL_APP"):
        llm.get_model()
    monkeypatch.setenv("MODEL_APP", "x")
    with pytest.raises(SystemExit, match="GEMINI_API_KEY"):
        llm.get_model()
