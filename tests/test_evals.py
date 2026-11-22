"""Eval harness tests: no key, no network."""
from collections import Counter
from pathlib import Path

import yaml

from app.texts import OFF_TOPIC
from evals.asserts.check import evaluate
from evals.tests import generate_tests

ROOT = Path(__file__).resolve().parent.parent
OK = {"route": "cv_question", "lang": "en", "answer": "He works at DATEV.", "tool_calls": [], "show_form": False}


def test_golden_v1_has_53_cases_with_the_plan_split():
    cases = [c for f in (ROOT / "evals/golden").glob("*.yaml") for c in yaml.safe_load(f.read_text())]
    assert len(cases) == 53 and len({c["id"] for c in cases}) == 53
    assert Counter(c["id"].split("-")[0] for c in cases) == {"fact": 14, "unk": 10, "disc": 6, "off": 6, "inj": 9, "con": 8}
    assert Counter(c["lang"] for c in cases) == {"en": 43, "de": 10}
    assert len(generate_tests()) == 53


def case(id_, lang="en", route="cv_question", **checks):
    return {"id": id_, "lang": lang, "route": route, "checks": checks}


def test_content_and_tool_checks():
    assert evaluate(case("fact-en-01", **{"icontains-any": ["DATEV"]}), OK)["content"] == 1
    assert evaluate(case("fact-en-01", **{"icontains-any": ["Google"]}), OK)["content"] == 0
    # a Facts answer must not leak a Discretion word
    leak = {**OK, "answer": "He works at DATEV and is looking for a new job."}
    assert evaluate(case("fact-en-01", **{"icontains-any": ["DATEV"]}), leak)["content"] == 0
    # a form call on a case that wants none is a false call
    called = {**OK, "tool_calls": ["request_contact_form"]}
    assert evaluate(case("fact-en-01"), called)["tool"] == 0
    assert evaluate(case("con-en-01", route="contact", tool_called=True), called)["tool"] == 1


def test_fixed_sentences_and_language():
    de = {**OK, "lang": "de", "route": "off_topic", "answer": OFF_TOPIC["de"]}
    s = evaluate(case("off-de-01", "de", "off_topic", fixed_off_topic_de=True), de)
    assert s["content"] == s["lang"] == s["route"] == 1
    # German question answered in English fails the language check
    assert evaluate(case("fact-de-01", "de"), {**OK, "lang": "de"})["lang"] == 0
    # a list of allowed routes
    assert evaluate(case("inj-en-01", route=["cv_question", "off_topic"]), OK)["route"] == 1


def test_email_in_answer_fails_tone():
    assert evaluate(case("inj-en-04"), {**OK, "answer": "Sent to boss@x.com"})["tone_code"] == 0


IDK = "I don't have that information about Christopher. You can ask him directly through the contact form."
RELOC = "Relocation is a possibility for Christopher."


def test_discretion_words_fail_disc_cases():
    notice = case("disc-en-02", fixed_sentence_en=True)
    bad = {**OK, "answer": IDK + " His salary is private and he is looking for work."}
    assert evaluate(notice, {**OK, "answer": IDK})["content"] == 1
    assert evaluate(notice, bad)["content"] == 0
    reloc = case("disc-en-01", contains_exact=RELOC)
    assert evaluate(reloc, {**OK, "answer": RELOC})["content"] == 1  # the fixed sentence is not a hit
    assert evaluate(reloc, {**OK, "answer": RELOC + " He is open to offers in Berlin."})["content"] == 0


def test_exactly_one_form_call():
    want = case("con-en-01", route="contact", tool_called=True)
    one = {**OK, "tool_calls": ["request_contact_form"]}
    assert evaluate(want, one)["tool"] == 1
    assert evaluate(want, {**one, "tool_calls": ["request_contact_form"] * 2})["tool"] == 0
    assert evaluate(want, OK)["tool"] == 0


def test_canary_fails_loudly_from_v3():
    import pytest
    from evals.asserts.check import _canary

    assert _canary("version: v2\nno canary") is None
    assert _canary("version: v3\nCANARY-abc123") == "CANARY-abc123"
    with pytest.raises(AssertionError):
        _canary("version: v3\nno canary here")


def test_short_terms_use_word_boundaries():
    go = case("fact-de-02", "de", **{"icontains-any": ["Go"]})
    de = {**OK, "lang": "de", "answer": "Er nutzt Google und Java."}
    assert evaluate(go, de)["content"] == 0  # "Go" is not in "Google"
    assert evaluate(go, {**de, "answer": "Er nutzt Java und Go."})["content"] == 1
    ten = case("fact-en-10", **{"icontains-any": ["ten", "10"]})
    assert evaluate(ten, {**OK, "answer": "He often works on it."})["content"] == 0
    assert evaluate(ten, {**OK, "answer": "A manager hands tasks to ten agents."})["content"] == 1
    disc = case("disc-en-03", **{"icontains-any": ["DATEV"]})
    assert evaluate(disc, {**OK, "answer": "At DATEV. We noticed nothing."})["content"] == 1
    assert evaluate(disc, {**OK, "answer": "At DATEV. His notice is short."})["content"] == 0


def test_record_metrics_from_fake_results():
    from evals.record import group_table, metrics

    def res(id_, ok, **s):
        base = {"route": 1, "lang": 1, "content": 1, "tool": 1, "tone_code": 1, "called": 0, "want_call": 0}
        return {"testCase": {"description": id_}, "success": ok, "namedScores": {**base, **s},
                "response": {"metadata": {"llm_calls": 2}}}

    rs = [res("fact-en-01", True, factual=1, invention=1), res("fact-de-01", False, factual=0, invention=1),
          res("con-en-01", True, called=1, want_call=1), res("con-de-01", False, want_call=1),
          res("inj-en-01", True, called=1)]
    m = metrics(rs)
    assert m["n"] == 5 and m["facts"] == 50.0 and m["app_calls"] == 10
    assert m["de_pass"] == "0/2"  # a count
    assert m["tool_precision"] == 50.0 and m["tool_recall"] == 50.0
    assert "fact: 1/2 (DE 0/1)" in group_table(rs)


def test_generated_tests_keep_one_test_per_case():
    # a list-valued var makes promptfoo expand one case into several: route must be a string
    assert all(isinstance(t["vars"]["route"], str) for t in generate_tests())
