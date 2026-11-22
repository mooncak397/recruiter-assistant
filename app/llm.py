"""The one place that builds the chat model. Model name and key come from the environment."""
import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model


def get_model():
    load_dotenv()  # reads .env if it exists; real env vars win
    name = os.environ.get("MODEL_APP")
    if not name:
        raise SystemExit("MODEL_APP is not set. Copy .env.example to .env.")
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        raise SystemExit("GEMINI_API_KEY is not set. Put it in .env (see README).")
    return init_chat_model(name, model_provider="google_genai", temperature=0)
