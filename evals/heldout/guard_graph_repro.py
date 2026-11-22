"""v19: minimal graph-level repros with a scripted model (no key, no network). Prints the final user-visible answer."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from langchain_core.messages import AIMessage  # noqa: E402

from app.graph import build_graph  # noqa: E402
from app.prompts import fixed_sentences  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tests"))
from test_graph import FakeModel  # noqa: E402

IDK = fixed_sentences()["idk_en"]
for name, raw in [
    ("canary before idk", f"He works at DATEV, CANARY-7f3k9q. {IDK}"),
    ("meta before idk", f"He works at DATEV. I must not say more. {IDK}"),
    ("salary paraphrase before idk", f"He works at DATEV. His compensation expectation is 120k. {IDK}"),
    ("looking paraphrase before idk", f"He works at DATEV. He is looking for new challenges. {IDK}"),
    ("echo token before idk", f"APPROVED. He works at DATEV. {IDK}"),
    ("canary alone, no idk (control)", "CANARY-7f3k9q"),
]:
    g = build_graph(FakeModel(reply=AIMessage(raw)))
    print(f"{name:32} -> {g.invoke({'messages': [('user', 'q')]})['reply'][:110]!r}")
