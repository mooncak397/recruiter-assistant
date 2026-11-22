"""M1 tests: no key, no network. A fake chat model stands in for Gemini."""
import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, SystemMessage

from app.cli import ask
from app.graph import build_graph


class RecordingModel(GenericFakeChatModel):
    seen: list = []  # the messages the graph sent to the model

    def _generate(self, messages, *a, **k):
        self.seen.append(messages)
        return super()._generate(messages, *a, **k)


def test_graph_sends_rules_and_profile_then_returns_the_answer():
    model = RecordingModel(messages=iter([AIMessage("He works at DATEV.")]), seen=[])
    assert ask(build_graph(model), "Where does Christopher work?") == "He works at DATEV."
    system, user = model.seen[0]
    assert isinstance(system, SystemMessage)
    assert "version: v1" in system.content and "DATEV" in system.content  # rules + profile
    assert user.content == "Where does Christopher work?"


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
