"""Usage: uv run python -m app.cli "Where does Christopher work?" """
import sys

from app.graph import build_graph
from app.llm import get_model


def ask(graph, question: str) -> str:
    result = graph.invoke({"messages": [("user", question)]})
    return result["messages"][-1].text


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python -m app.cli "<question>"')
    print(ask(build_graph(get_model()), sys.argv[1]))
