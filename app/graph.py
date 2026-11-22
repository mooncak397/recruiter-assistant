"""M1: a LangGraph graph with one node that answers from the system prompt. M2 adds the router."""
from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph

from app.prompts import system_prompt


def build_graph(model):
    prompt = system_prompt()

    def answer(state: MessagesState):
        return {"messages": [model.invoke([SystemMessage(prompt), *state["messages"]])]}

    g = StateGraph(MessagesState)
    g.add_node("answer", answer)
    g.add_edge(START, "answer")
    g.add_edge("answer", END)
    return g.compile()
