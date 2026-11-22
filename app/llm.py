"""The one place that builds the chat models. Provider, model name and key come from the environment.
PROVIDER_APP / PROVIDER_JUDGE: "google" (default, free tier) or "anthropic"."""
import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model


def _build(provider: str, name_var: str):
    load_dotenv()  # reads .env if it exists; real env vars win
    name = os.environ.get(name_var)
    if not name:
        raise SystemExit(f"{name_var} is not set. Copy .env.example to .env.")
    if provider == "anthropic":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise SystemExit("ANTHROPIC_API_KEY is not set. Put it in .env (see README).")
        # No temperature: the current Claude models reject non-default sampling values.
        return init_chat_model(name, model_provider="anthropic", max_tokens=4096)
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        raise SystemExit("GEMINI_API_KEY is not set. Put it in .env (see README).")
    return init_chat_model(name, model_provider="google_genai", temperature=0)


def get_model():
    load_dotenv()
    return _build(os.environ.get("PROVIDER_APP", "google"), "MODEL_APP")


def get_judge():
    load_dotenv()
    return _build(os.environ.get("PROVIDER_JUDGE", "google"), "MODEL_JUDGE")
