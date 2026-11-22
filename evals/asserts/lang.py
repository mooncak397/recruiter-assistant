"""Language check (plan section 7): the lang field must match, and a small function-word count must agree."""
import re

EN = {"the", "and", "is", "not", "you", "for", "he", "his", "of", "to", "at"}
DE = {"der", "die", "und", "nicht", "sie", "ist", "für", "ein", "eine", "das", "bei", "er"}


def words_agree(text: str, lang: str) -> bool:
    words = re.findall(r"[a-zäöüß]+", text.lower())
    en, de = sum(w in EN for w in words), sum(w in DE for w in words)
    return de >= en if lang == "de" else en >= de  # a tie passes: very short answers


def lang_ok(out: dict, expected: str) -> bool:
    return out["lang"] == expected and words_agree(out["answer"], expected)
