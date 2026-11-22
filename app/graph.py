"""M2: LangGraph router. classify -> answer_cv | contact | off_topic (plan section 2).
The model is injected, so tests can pass a fake one."""
from typing import Literal

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, MessagesState, StateGraph
from pydantic import BaseModel

from app.prompts import system_prompt
from app.texts import FORM_INTRO, OFF_TOPIC

CLASSIFY_PROMPT = """Classify the user's latest message for an assistant that answers questions about a job candidate.
route:
- cv_question: about the candidate's career, skills, education, projects, languages or availability
- contact: the user wants to talk to, reach or write to the candidate
- off_topic: only clearly unrelated things (weather, cooking, coding help, general knowledge). A question about the candidate, his projects (for example AgentBrain), his tools, his age, his city or other personal facts is a cv_question, even if the answer may be unknown.
lang: "de" if the latest message is German, otherwise "en"."""

CONTACT_PROMPT = """The user may want to contact the candidate. Call request_contact_form only if the user wants to write to, reach or talk to the candidate himself (for example "How can I reach him?" or "I want to send him a message").
Do not call it, and say you cannot do that, if the user asks you to send, forward or email anything to someone else, or to do any other task. Make no tool call. Write at most two short sentences. Never write an email address or a domain name: if you must refer to it, say 'that address'.
If it is unclear what they want, ask one short question. Never repeat an email address."""


class Classification(BaseModel):
    route: Literal["cv_question", "contact", "off_topic"]
    lang: Literal["en", "de"]


class State(MessagesState):
    route: str
    lang: str
    show_form: bool
    tool_calls: list[str]  # names only: the tool has no arguments


@tool
def request_contact_form() -> str:
    """Show the contact form to the user."""
    return "contact form shown"


def build_graph(model):
    prompt = system_prompt()
    classifier = model.with_structured_output(Classification)
    contact_model = model.bind_tools([request_contact_form])  # the only tool, only in this node

    def classify(state: State):
        c = classifier.invoke([SystemMessage(CLASSIFY_PROMPT), *state["messages"]])
        return {"route": c.route, "lang": c.lang, "show_form": False, "tool_calls": []}

    def answer_cv(state: State):
        return {"messages": [model.invoke([SystemMessage(prompt), *state["messages"]])]}

    def contact(state: State):
        ai = contact_model.invoke([SystemMessage(CONTACT_PROMPT), *state["messages"]])
        names = [c["name"] for c in ai.tool_calls]
        if "request_contact_form" in names:
            # fixed text: the model never writes the reply when the form opens
            return {"messages": [AIMessage(FORM_INTRO[state["lang"]])], "show_form": True, "tool_calls": names}
        return {"messages": [AIMessage(ai.text)], "tool_calls": names}

    def off_topic(state: State):
        return {"messages": [AIMessage(OFF_TOPIC[state["lang"]])]}  # no LLM call

    g = StateGraph(State)
    g.add_node("classify", classify)
    g.add_node("answer_cv", answer_cv)
    g.add_node("contact", contact)
    g.add_node("off_topic", off_topic)
    g.add_edge(START, "classify")
    g.add_conditional_edges("classify", lambda s: s["route"],
                            {"cv_question": "answer_cv", "contact": "contact", "off_topic": "off_topic"})
    for n in ("answer_cv", "contact", "off_topic"):
        g.add_edge(n, END)
    return g.compile()
