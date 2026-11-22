from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def system_prompt() -> str:
    """Rules first, then the profile. Both files are public in the repo."""
    rules = (ROOT / "prompts/rules.md").read_text()
    profile = (ROOT / "profile/profile.md").read_text()
    return f"{rules}\n\n# Profile\n\n{profile}"
