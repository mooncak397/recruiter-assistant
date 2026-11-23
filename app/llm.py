"""The one place that builds the chat models. Provider, model name and key come from the environment.
PROVIDER_APP / PROVIDER_JUDGE: "google" (default, free tier) or "anthropic".
MODEL_APP is optional (a cheap default per provider); MODEL_JUDGE must be set, so an eval never runs on a guessed judge."""
import os

APP_DEFAULTS = {"google": "gemini-3.5-flash-lite", "anthropic": "claude-haiku-5-5"}

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model


def _build(provider: str, name_var: str, default: str | None = None):
    load_dotenv()  # reads .env if it exists; real env vars win
    name = os.environ.get(name_var) or default
    if not name:
        raise SystemExit(f"{name_var} is not set. Copy .env.example to .env.")
    if provider == "anthropic":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise SystemExit("ANTHROPIC_API_KEY is not set. Put it in .env (see README).")
        # No temperature: the current Claude models reject non-default sampling values.
        return init_chat_model(name, model_provider="anthropic", max_tokens=4096)
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        raise SystemExit("GEMINI_API_KEY is not set. Put it in .env (see README).")
    # a hung free-tier call must not block an eval run or a chat turn: 60 s, then the graph answers BUSY
    return init_chat_model(name, model_provider="google_genai", temperature=0,
                           timeout=float(os.environ.get("MODEL_TIMEOUT", "60")))


def get_model():
    load_dotenv()
    provider = os.environ.get("PROVIDER_APP", "google")
    return _build(provider, "MODEL_APP", APP_DEFAULTS.get(provider))


def get_judge():
    load_dotenv()
    return _build(os.environ.get("PROVIDER_JUDGE", "google"), "MODEL_JUDGE")
