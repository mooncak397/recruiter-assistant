"""M0 checks from the plan (section 8). No network, no model."""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

# The four fixed sentences, character for character (ADR-007).
FIXED = [
    "I don't have that information about Christopher. You can ask him directly through the contact form.",
    "Dazu habe ich keine Informationen über Christopher. Sie können ihn direkt über das Kontaktformular fragen.",
    "Relocation is a possibility for Christopher.",
    "Ein Umzug ist für Christopher eine Möglichkeit.",
]

# Patterns for private VALUES. The profile may name the words (its "not in this profile" list).
PRIVATE = [
    r"(\+\d|\b0\d)[\d /-]{7,}\d",              # phone number (starts with + or 0)
    r"\b\w+(straße|strasse|str\.)\s*\d+",        # street and house number
    r"\b\d{1,2}\.\d{1,2}\.(19|20)\d{2}\b",       # dd.mm.yyyy (birth date style)
    r"\b(geboren|born (on|in))\b",
    r"Kündigungsfrist",
    r"notice period",
    r"(CHF|EUR|€)\s*\d|\d\s*(CHF|EUR|€)",        # salary figure
    r"(prefers|wants|would like) to (work|live) in",
]


def test_structure():
    for p in ["README.md", "profile/profile.md", "prompts/rules.md", ".gitignore", ".env.example",
              "docs/adr", "evals/golden", "tests", "app", "web", ".github/workflows"]:
        assert (ROOT / p).exists(), p
    assert len(list((ROOT / "docs/adr").glob("00[1-7]-*.md"))) == 7


# Shared word list (plan section 7). The "not" section may name these words, the rest may not.
WORDS = ["notice", "Kündigungsfrist", "relocat", "Umzug", "umziehen", "move to", "prefers to work in",
         "salary", "Lohn", "Gehalt", "Switzerland", "Schweiz", "looking for", "open to offers",
         "auf Stellensuche", "offen für", "Geburtsdatum"]
EMAIL = r"[\w.+-]+@[\w-]+\.[\w.-]+"
NOT_HEADING = "## What Christopher is not / skills he does not have"


def test_profile_outside_not_section_has_no_private_words():
    rest = (ROOT / "profile/profile.md").read_text().split(NOT_HEADING)[0]
    for w in WORDS:
        assert w.lower() not in rest.lower(), w
    assert not re.search(EMAIL, rest)


def test_profile():
    text = (ROOT / "profile/profile.md").read_text()
    assert len(text.split()) < 5000
    assert "## What Christopher is not / skills he does not have" in text
    for pat in PRIVATE:
        assert not re.search(pat, text, re.I), pat
    assert not re.search(EMAIL, text)


def test_rules_has_fixed_sentences():
    rules = (ROOT / "prompts/rules.md").read_text()
    assert rules.startswith("version: v")
    for s in FIXED:
        assert s in rules


def test_no_nickname_anywhere():
    for f in ROOT.rglob("*"):
        if f.is_file() and not {".git", ".venv", ".pytest_cache", "__pycache__"} & set(f.parts):
            assert "chr" + "izz" not in f.read_text(errors="ignore").lower(), f  # split so this file passes too


def test_golden_set():
    cases = []
    for name, n in [("facts", 14), ("unknown", 10), ("discretion", 6)]:
        c = yaml.safe_load((ROOT / f"evals/golden/{name}.yaml").read_text())
        assert len(c) == n, name
        cases += c
    ids = [c["id"] for c in cases]
    assert len(set(ids)) == 30
    for c in cases:
        assert {"id", "lang", "vars", "route", "expected", "assert"} <= c.keys(), c["id"]
        assert c["lang"] in ("en", "de")
        if c["lang"] == "de":
            assert "reference_en" in c or c["id"].startswith("unk-de"), c["id"]
    # the exact relocation sentences used by the cases must be the rules.md ones
    for c in cases:
        if "contains_exact" in c["assert"]:
            assert c["assert"]["contains_exact"] in FIXED


def test_golden_assert_keys_are_documented():
    readme = (ROOT / "evals/golden/README.md").read_text()
    keys = set()
    for f in (ROOT / "evals/golden").glob("*.yaml"):
        for case in yaml.safe_load(f.read_text()):
            keys |= case["assert"].keys()
    missing = {k for k in keys if f"`{k}`" not in readme}
    assert not missing, missing
