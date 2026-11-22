from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def system_prompt() -> str:
    """Rules first, then the profile. Both files are public in the repo."""
    rules = (ROOT / "prompts/rules.md").read_text()
    profile = (ROOT / "profile/profile.md").read_text()
    return f"{rules}\n\n# Profile\n\n{profile}"


def fixed_sentences() -> dict[str, str]:
    """The four fixed sentences, read from rules.md (their single source)."""
    import re

    keys = {("I don't know", "EN"): "idk_en", ("I don't know", "DE"): "idk_de",
            ("Relocation", "EN"): "reloc_en", ("Relocation", "DE"): "reloc_de"}
    found = re.findall(r"^- (I don't know|Relocation) \((EN|DE)\): (.+)$",
                       (ROOT / "prompts/rules.md").read_text(), re.M)
    return {keys[(a, b)]: s for a, b, s in found}
