"""Usage: uv run python -m app.cli "Where does Christopher work?" """
import sys

from app.graph import build_graph
from app.llm import get_model


def ask(graph, question: str) -> dict:
    return graph.invoke({"messages": [("user", question)]})


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python -m app.cli "<question>"')
    state = ask(build_graph(get_model()), sys.argv[1])
    print(f"[route={state['route']} lang={state['lang']} show_form={state['show_form']}]", file=sys.stderr)
    print(state["messages"][-1].text)
