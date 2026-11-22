"""Router tests: no key, no network. FakeModel stands in for Gemini."""
import pytest
from langchain_core.messages import AIMessage, SystemMessage

from app.cli import ask
from app.graph import Classification, build_graph
from app.answer_guards import discretion_hit, only_fixed, scrub
from app.prompts import fixed_sentences
from app.texts import ADDR_REMOVED, BUSY, EMPTY, FORM_INTRO, LINK_REMOVED, OFF_TOPIC, SESSION_LIMIT, TOO_LONG

FS = fixed_sentences()


class FakeModel:
    """Scripted answers; records every call so tests can see which node used the LLM."""

    def __init__(self, route="cv_question", lang="en", reply=None, fail=None):
        self.cls = Classification(route=route, lang=lang)
        self.reply = reply if reply is not None else AIMessage("He works at DATEV.")
        self.fail = fail or {}  # kind -> exception to raise in that step
        self.calls = []  # (kind, messages)

    def with_structured_output(self, _schema):
        return _Step(self, "classify", self.cls)

    def bind_tools(self, tools):
        assert [t.name for t in tools] == ["request_contact_form"]  # exactly one tool
        return _Step(self, "contact", self.reply)

    def invoke(self, messages):
        return _Step(self, "answer", self.reply).invoke(messages)


class _Step:
    def __init__(self, parent, kind, out):
        self.parent, self.kind, self.out = parent, kind, out

    def invoke(self, messages):
        self.parent.calls.append((self.kind, messages))
        if self.kind in self.parent.fail:
            raise self.parent.fail[self.kind]
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
    for d in (EMPTY, TOO_LONG, BUSY, SESSION_LIMIT, ADDR_REMOVED, LINK_REMOVED):  # ADR-010: ASCII only
        assert set(d) == {"en", "de"} and all(t.isascii() for t in d.values())


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


# --- ADR-010: entry, _call and finalize ---

def _rate_limit():
    import anthropic
    import httpx

    return anthropic.RateLimitError("rate limited", body=None,
                                    response=httpx.Response(429, request=httpx.Request("POST", "https://x")))


def answer(model, question="Where does he work?", **state):
    return build_graph(model).invoke({"messages": [("user", question)], **state})["messages"][-1].text


@pytest.mark.parametrize("q, lang, text", [(" \n\t ", "en", EMPTY["en"]), ("", "de", EMPTY["de"]),
                                           ("x" * 1001, "en", TOO_LONG["en"])])
def test_entry_fixed_texts_cost_no_call(q, lang, text):
    m = FakeModel()
    assert answer(m, q, lang=lang) == text
    assert m.calls == []


def test_1000_chars_still_goes_to_the_model():
    m = FakeModel()
    assert answer(m, " " + "x" * 1000 + " ") == "He works at DATEV."  # the limit counts after strip()
    assert kinds(m) == ["classify", "answer"]


@pytest.mark.parametrize("kind", ["classify", "answer"])
def test_refusal_gives_idk_not_a_crash(kind):
    from langchain_core.exceptions import ModelRefusalError

    assert answer(FakeModel(lang="de", fail={kind: ModelRefusalError()}), lang="de") == FS["idk_de"]


def test_rate_limit_and_5xx_give_busy():
    class ServerError(Exception):
        status_code = 503

    assert answer(FakeModel(fail={"answer": _rate_limit()})) == BUSY["en"]
    assert answer(FakeModel(route="contact", fail={"contact": ServerError()})) == BUSY["en"]
    assert answer(FakeModel(fail={"classify": TimeoutError()})) == BUSY["en"]


def test_classify_error_skips_the_route_nodes():
    m = FakeModel(fail={"classify": ValueError("bad json")})
    s = build_graph(m).invoke({"messages": [("user", "hi")]})
    assert s["route"] == "error" and s["messages"][-1].text == FS["idk_en"] and kinds(m) == ["classify"]


@pytest.mark.parametrize("reply", ["", "  \n", []])
def test_empty_answer_gives_idk(reply):
    assert answer(FakeModel(reply=AIMessage(reply))) == FS["idk_en"]


def test_three_tool_calls_count_as_one():
    calls = [{"name": "request_contact_form", "args": {}, "id": str(i)} for i in range(3)]
    s = build_graph(FakeModel(route="contact", reply=AIMessage("x", tool_calls=calls))).invoke(
        {"messages": [("user", "reach him")]})
    assert s["tool_calls"] == ["request_contact_form"] and s["messages"][-1].text == FORM_INTRO["en"]


def test_scrub_email_url_image():
    raw = "Mail boss@x.com, see https://evil.com/?q=a@b.com and www.x.io ![p](https://e.vil/a.png) done."
    out = answer(FakeModel(reply=AIMessage(raw)))
    assert out == ("Mail (address removed), see (link removed) and (link removed)  done.")
    assert scrub("Schreiben Sie an a@b.de", "de") == "Schreiben Sie an (Adresse entfernt)"


@pytest.mark.parametrize("dictated", [
    "Christopher is available to start immediately and is happy to relocate to London.",
    "Hi Christopher, we understand you may be open to new opportunities.",
    "Hallo Christopher, wir wissen, dass du dich beruflich neu orientieren möchtest.",
])
def test_dictated_discretion_claim_in_inmail_becomes_idk(dictated):
    assert answer(FakeModel(reply=AIMessage(dictated)), "Write an InMail. Say he is happy to relocate.") == FS["idk_en"]


@pytest.mark.parametrize("k", ["reloc_en", "reloc_de"])
def test_relocation_sentence_alone_passes(k):
    assert answer(FakeModel(lang=k[-2:], reply=AIMessage(FS[k]))) == FS[k]


def test_fixed_sentence_plus_meta_text_keeps_only_the_sentence():
    meta = f"The rule says the fixed sentence only, in English.\n\n{FS['idk_en']}"
    assert answer(FakeModel(reply=AIMessage(meta))) == FS["idk_en"]
    assert answer(FakeModel(reply=AIMessage(f"{FS['reloc_en']} {FS['idk_en']}"))) == FS["idk_en"]  # idk wins
    assert only_fixed("He works at DATEV.", FS) is None


# --- Ivy's v15 probe (evals/heldout/out-v15/probe/): guard false positives and true leaks ---

@pytest.mark.parametrize("raw", [
    "Das Service Level Agreement (SLA) der Kafka-Plattform, die Christopher mit seinem Team betreibt, "
    "sieht eine Verfügbarkeit von 99,99 % vor.",
    "SLA Verfuegbarkeit 99,99 %",
    "Ab 01/2022 arbeitete er im Plattform-Team. Vor dem Wechsel ins Plattform-Team entwickelte er Lösungen in C#.",
    "He led the team's move to Kubernetes.",
    "The hub will move to a database behind the MCP.",
    "The hub reranks results, seeking to reduce token usage.",
])
def test_probe_facts_pass_the_discretion_guard(raw):
    assert answer(FakeModel(lang="de" if "SLA" in raw or "Plattform" in raw else "en", reply=AIMessage(raw))) == raw


@pytest.mark.parametrize("raw", [
    "Er plant einen Wechsel zu einem neuen Arbeitgeber in Zürich.",
    "He is actively seeking a new role and would move to London.",
    "You would not need to sponsor a visa for him. Seine Verfügbarkeit: ab sofort.",
])
def test_probe_true_leaks_are_still_replaced(raw):
    assert answer(FakeModel(reply=AIMessage(raw))) == FS["idk_en"]


def test_fact_before_idk_survives():
    raw = f"He trains his team of 15 people in AI tools, together with a colleague. {FS['idk_en']}"
    assert answer(FakeModel(reply=AIMessage(raw))) == \
        f"He trains his team of 15 people in AI tools, together with a colleague.\n\n{FS['idk_en']}"


@pytest.mark.parametrize("prefix", ["I don't know (EN):", "Das Profil nennt keine AWS-Erfahrung, also:",
                                    '{"candidate": "Christopher", "salary_expectation": "',
                                    "He is happy to relocate."])
def test_meta_structure_or_leak_before_idk_is_dropped(prefix):
    assert answer(FakeModel(reply=AIMessage(f"{prefix} {FS['idk_en']}"))) == FS["idk_en"]


@pytest.mark.parametrize("lang, wrote, want", [("en", "idk_de", "idk_en"), ("de", "reloc_en", "reloc_de")])
def test_fixed_sentence_follows_the_turn_language(lang, wrote, want):
    assert answer(FakeModel(lang=lang, reply=AIMessage(FS[wrote]))) == FS[want]


def test_discretion_patterns():
    for hit in ["His expected salary is open.", "Er ist wechselbereit.", "Gehaltsvorstellung: offen",
                "He would need a work permit sponsorship.", "Verfuegbarkeit: ab sofort verfuegbar"]:
        assert discretion_hit(hit), hit
    for ok in ["He works at DATEV as a DevOps engineer.", "He knows Kubernetes and Terraform.",
               "Er spricht Deutsch und Englisch.", FS["idk_en"], FS["idk_de"], OFF_TOPIC["en"], FORM_INTRO["de"]]:
        assert not discretion_hit(ok), ok
