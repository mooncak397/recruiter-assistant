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
