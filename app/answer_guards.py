"""Deterministic answer guards (ADR-010, decisions 2 and 3). Pure functions, no model call.
The `finalize` node in app/graph.py runs them; evals/asserts/check.py imports DISCRETION_PATTERNS."""
import re

from app.texts import ADDR_REMOVED, LINK_REMOVED


def _w(term, suffix=r"\w*"):
    """Word-start boundary; the default suffix makes the term a prefix ("opportunit" -> "opportunities")."""
    return r"(?<!\w)" + term + suffix + r"(?!\w)"


# One source for the app guard and the eval word check. Case-insensitive.
# Old terms keep their fixed suffixes (ADR-008): "salaries" and "Gehaelter" hit, "gehalten" and "Schweizer" do not.
_PLACE = (r"(?:Zurich|Zürich|Zuerich|Basel|Bern|Geneva|Genf|Lausanne|Zug|London|Berlin|Munich|München|Muenchen"
          r"|Hamburg|Frankfurt|Vienna|Wien|Amsterdam|Dublin|abroad|Ausland|another (?:city|country)|a new (?:city|country))")
_JOB = r"(?:role|position|job|opportunit\w*|challenge\w*|employer|company)"
_VERF = r"Verf(?:ü|ue)gbarkeit"

DISCRETION_PATTERNS = [
    _w("notice", "(?:s)?"), _w("Kündigung", "(?:s\\w*|en)?"), _w("relocat", "(?:e|es|ed|ing|ion)"),
    _w("Umzug", "(?:s|es)?"), _w("umzieh", "(?:en|e|t|st)"), _w("prefers to work in", ""),
    _w("salar", "(?:y|ies)"), _w("Lohn", "(?:s|es)?"), _w("Gehalt", "(?:s|es)?"), _w("Gehälter", ""),
    _w("earns", ""), _w("Switzerland", ""), _w("Schweiz", ""), _w("looking for a new", ""),
    _w("job search", ""), _w("open to offers", ""), _w("Stellensuche", ""), _w("offen für", ""),
    _w("Jobwechsel", ""), _w("Stellenwechsel", ""), _w("Arbeitgeberwechsel", ""), _w("Wechselwunsch"),
    # ADR-010 additions (red-team finding 1)
    _w("open to new"), _w("new opportunit"), _w("exploring the market"), _w("available immediately"),
    _w("available to start"), _w("start immediately"), _w("immediately available"), _w("ready to move"),
    _w("willing to move"), _w("work permit"), _w("expected salary"), _w("neu orientieren"),
    _w("Neuorientierung"), _w("wechseln m(?:ö|oe)chte"), _w("wechselbereit"), _w("ab sofort verf"),
    _w("Gehaltsvorstellung"), _w("Wechselmotivation"), _w("Kuendigungsfrist"),
    # Ambiguous words only in a person, place or job context (v15 red-team: "SLA Verfuegbarkeit 99,99 %",
    # "Wechsel ins Plattform-Team", "move to Kubernetes", "seeking to reduce", "a sponsor of the circle" are facts)
    r"(?<!\w)move to (?:the )?" + _PLACE + r"(?!\w)", r"(?<!\w)move to (?:a new|another) " + _JOB,
    r"(?<!\w)(?:actively seeking|seeking (?:a |an |his |new |next |other |another )*" + _JOB + ")",
    r"(?<!\w)sponsor\w*[^.\n]{0,40}(?:visa|permit)", r"(?<!\w)(?:visa|permit)[^.\n]{0,40}sponsor",
    r"(?<!\w)Wechsel\w*[^.\n]{0,40}(?<!\w)(?:Arbeitgeber|Firma|Unternehmen|Stelle|Job\b|" + _PLACE + ")",
    r"(?<!\w)beruflich\w*\s+(?:\w+\s+)?Wechsel",
    r"(?<!\w)(?:seine[nmr]?|ihre[nmr]?|Ihre[nmr]?)\s+" + _VERF, r"(?<!\w)" + _VERF + r"\s*[:(]",
    r"(?<!\w)" + _VERF + r"\s+(?:ab|zum|per|innerhalb)(?!\w)", r"^\W*" + _VERF + r"(?!\w)",
]
_DISCRETION = re.compile("|".join(DISCRETION_PATTERNS), re.I | re.M)

# The broad forms stay in the eval word check (evals/asserts/check.py), which may be stricter than the app.
EVAL_ONLY_PATTERNS = [_w("move to", ""), _w("seeking", ""), _w("Wechsel", "(?:n|s)?"), _w("sponsor"), _w(_VERF, "")]

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
URL = re.compile(r"https?://\S+|www\.\S+")


# Thought or rule text the model sometimes writes next to a fixed sentence (red-team finding 6)
META = re.compile(r"(?<!\w)(?:rules?|the user|wait|instructions?|fixed sentence|system prompt|Regel\w*|"
                  r"der (?:Nutzer|Benutzer)|Anweisung\w*|I don't know|profiles?|Profil\w*|the question|die Frage)(?!\w)"
                  r"|\((?:EN|DE)\)|:\s*$|[{}\[\]<>|]", re.I)  # a cut JSON, XML or table is not a fact text


def only_fixed(text: str, fixed: dict[str, str]) -> tuple[str, str] | None:
    """(kind, kept) if the reply contains a fixed sentence, else None. kind = "idk" or "reloc".
    kept = the fact text before an idk sentence, if it has no Discretion hit and no meta text ("" otherwise).
    Text after the sentence and text around a relocation sentence are dropped. Both kinds: idk wins."""
    found = sorted((k for k, s in fixed.items() if s in text), key=lambda k: not k.startswith("idk"))
    if not found:
        return None
    kind = found[0][:-3]
    kept = text.split(fixed[found[0]])[0].strip() if kind == "idk" and len(found) == 1 else ""
    if not re.search(r"\w", kept) or discretion_hit(kept) or META.search(kept):
        kept = ""
    return kind, kept


def discretion_hit(text: str) -> bool:
    """No negation stripping here (fail closed); check.py strips negations for the eval only."""
    return _DISCRETION.search(text) is not None


def scrub(text: str, lang: str) -> str:
    """Images first, then URLs, then addresses, so an address inside a URL goes with the URL."""
    text = IMAGE.sub("", text)
    text = URL.sub(LINK_REMOVED[lang], text)
    return EMAIL.sub(ADDR_REMOVED[lang], text)
