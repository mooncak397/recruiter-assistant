"""Deterministic answer guards (ADR-010, decisions 2 and 3). Pure functions, no model call.
The `finalize` node in app/graph.py runs them; evals/asserts/check.py imports DISCRETION_PATTERNS."""
import re

from app.texts import ADDR_REMOVED, LINK_REMOVED


def _w(term, suffix=r"\w*"):
    """Word-start boundary; the default suffix makes the term a prefix ("opportunit" -> "opportunities")."""
    return r"(?<!\w)" + term + suffix + r"(?!\w)"


# One source for the app guard and the eval word check. Case-insensitive.
# Old terms keep their fixed suffixes (ADR-008): "salaries" and "Gehaelter" hit, "gehalten" and "Schweizer" do not.
DISCRETION_PATTERNS = [
    _w("notice", "(?:s)?"), _w("Kündigung", "(?:s\\w*|en)?"), _w("relocat", "(?:e|es|ed|ing|ion)"),
    _w("Umzug", "(?:s|es)?"), _w("umzieh", "(?:en|e|t|st)"), _w("move to", ""), _w("prefers to work in", ""),
    _w("salar", "(?:y|ies)"), _w("Lohn", "(?:s|es)?"), _w("Gehalt", "(?:s|es)?"), _w("Gehälter", ""),
    _w("earns", ""), _w("Switzerland", ""), _w("Schweiz", ""), _w("looking for a new", ""), _w("seeking", ""),
    _w("job search", ""), _w("open to offers", ""), _w("Stellensuche", ""), _w("offen für", ""),
    _w("Wechsel", "(?:n|s)?"), _w("Jobwechsel", ""), _w("Stellenwechsel", ""), _w("Arbeitgeberwechsel", ""),
    # ADR-010 additions (red-team finding 1)
    _w("open to new"), _w("new opportunit"), _w("exploring the market"), _w("available immediately"),
    _w("available to start"), _w("start immediately"), _w("immediately available"), _w("ready to move"),
    _w("willing to move"), _w("work permit"), _w("sponsor"), _w("expected salary"), _w("neu orientieren"),
    _w("Neuorientierung"), _w("wechseln m(?:ö|oe)chte"), _w("wechselbereit"), _w("ab sofort verf"),
    _w("Verf(?:ü|ue)gbarkeit"), _w("Gehaltsvorstellung"), _w("Wechselmotivation"), _w("Kuendigungsfrist"),
]
_DISCRETION = re.compile("|".join(DISCRETION_PATTERNS), re.I)

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
URL = re.compile(r"https?://\S+|www\.\S+")


def only_fixed(text: str, fixed: dict[str, str]) -> str | None:
    """The fixed sentence if the reply contains one (meta text around it is dropped), else None.
    `fixed` = fixed_sentences(). Both an idk and a relocation sentence: the idk sentence wins."""
    found = [s for k, s in fixed.items() if s in text]
    idk = [s for k, s in fixed.items() if k.startswith("idk") and s in text]
    return (idk or found or [None])[0]


def discretion_hit(text: str) -> bool:
    """No negation stripping here (fail closed); check.py strips negations for the eval only."""
    return _DISCRETION.search(text) is not None


def scrub(text: str, lang: str) -> str:
    """Images first, then URLs, then addresses, so an address inside a URL goes with the URL."""
    text = IMAGE.sub("", text)
    text = URL.sub(LINK_REMOVED[lang], text)
    return EMAIL.sub(ADDR_REMOVED[lang], text)
