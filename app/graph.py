"""LangGraph router (plan section 2, ADR-010):
entry -> classify -> answer_cv | contact | off_topic -> finalize. entry and finalize make no model call.
The model is injected, so tests can pass a fake one."""
import logging
from typing import Literal

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, MessagesState, StateGraph
from pydantic import BaseModel

from app.answer_guards import discretion_hit, only_fixed, scrub
from app.prompts import fixed_sentences, system_prompt
from app.texts import BUSY, EMPTY, FORM_INTRO, OFF_TOPIC, TOO_LONG

log = logging.getLogger(__name__)
MAX_CHARS = 1000

CLASSIFY_PROMPT = """Classify the user's latest message for an assistant that answers questions about a job candidate.
route:
- cv_question: about the candidate's career, skills, education, projects, languages or availability
- contact: the user wants to talk to, reach or send a message to the candidate through this site
- A request to draft or write a text (an email, an InMail, a LinkedIn message, a summary, a form), also a text addressed to the candidate, is a cv_question.
- off_topic: only clearly unrelated things (weather, cooking, coding help, general knowledge). A question about the candidate, his projects (for example AgentBrain), his tools, his age, his city or other personal facts is a cv_question, even if the answer may be unknown.
lang: the language of the user's own request in the latest message: "de" for German, otherwise "en". A quoted text does not count: "Translate this into English: '<German text>'" is "en"."""

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
    reply: str  # the node's reply; finalize checks it and appends the one AIMessage
    fixed: bool  # True = a code-chosen text, finalize returns it unchanged


@tool
def request_contact_form() -> str:
    """Show the contact form to the user."""
    return "contact form shown"


def _transport(e: Exception) -> bool:
    """429, 5xx, timeout or connection error (after the SDK's own retries)."""
    if getattr(e, "is_retryable", False):  # langchain_core ModelError subclasses
        return True
    code = getattr(e, "status_code", None) or getattr(e, "code", None)
    if isinstance(code, int) and (code == 429 or code >= 500):
        return True
    name, msg = type(e).__name__, str(e)
    return (any(k in name for k in ("Timeout", "Connection", "RateLimit", "ResourceExhausted", "ServiceUnavailable"))
            or "429" in msg or "RESOURCE_EXHAUSTED" in msg)


def build_graph(model):
    prompt = system_prompt()
    fixed = fixed_sentences()
    idk = {"en": fixed["idk_en"], "de": fixed["idk_de"]}
    classifier = model.with_structured_output(Classification)
    contact_model = model.bind_tools([request_contact_form])  # the only tool, only in this node

    def _call(fn, lang):
        """One model call. Returns (result, None), or (None, fixed reply) on any error: never raises."""
        try:
            out = fn()
            if out is None:  # structured output that did not parse
                raise ValueError("no parsed output")
            return out, None
        except Exception as e:  # refusal, parse error, transport: the user gets a fixed text, not a 500
            busy = _transport(e)
            log.warning("model_error class=%s busy=%s", type(e).__name__, busy)
            return None, (BUSY if busy else idk)[lang]

    def entry(state: State):
        lang = state.get("lang") or "en"  # the session's last lang; no model call to detect it
        out = {"route": "entry", "lang": lang, "show_form": False, "tool_calls": [], "reply": "", "fixed": False}
        text = state["messages"][-1].text.strip()
        if not text:
            return {**out, "reply": EMPTY[lang], "fixed": True}
        if len(text) > MAX_CHARS:
            return {**out, "reply": TOO_LONG[lang], "fixed": True}
        return out

    def classify(state: State):
        c, err = _call(lambda: classifier.invoke([SystemMessage(CLASSIFY_PROMPT), *state["messages"]]), state["lang"])
        if err:
            return {"route": "error", "reply": err, "fixed": True}
        return {"route": c.route, "lang": c.lang}

    def answer_cv(state: State):
        ai, err = _call(lambda: model.invoke([SystemMessage(prompt), *state["messages"]]), state["lang"])
        return {"reply": err, "fixed": True} if err else {"reply": ai.text}

    def contact(state: State):
        ai, err = _call(lambda: contact_model.invoke([SystemMessage(CONTACT_PROMPT), *state["messages"]]), state["lang"])
        if err:
            return {"reply": err, "fixed": True}
        if any(c["name"] == "request_contact_form" for c in ai.tool_calls):
            # one tool call at most; the model never writes the reply when the form opens
            return {"reply": FORM_INTRO[state["lang"]], "fixed": True, "show_form": True,
                    "tool_calls": ["request_contact_form"]}
        return {"reply": ai.text}

    def off_topic(state: State):
        return {"reply": OFF_TOPIC[state["lang"]], "fixed": True}  # no LLM call

    def finalize(state: State):
        lang, text, guard = state["lang"], state["reply"], None
        if not state["fixed"]:
            text = text.strip()
            if not text:
                text, guard = idk[lang], "empty"
            elif s := only_fixed(text, fixed):
                text, guard = s, ("fixed_sentence" if s != text else None)
            elif discretion_hit(text):
                text, guard = idk[lang], "discretion"
            elif (s := scrub(text, lang)) != text:
                text, guard = s, "scrub"
        if guard:
            log.info("guard=%s route=%s lang=%s", guard, state["route"], lang)
        return {"messages": [AIMessage(text)], "reply": text}

    g = StateGraph(State)
    for name, fn in [("entry", entry), ("classify", classify), ("answer_cv", answer_cv),
                     ("contact", contact), ("off_topic", off_topic), ("finalize", finalize)]:
        g.add_node(name, fn)
    g.add_edge(START, "entry")
    g.add_conditional_edges("entry", lambda s: "finalize" if s["fixed"] else "classify",
                            {"classify": "classify", "finalize": "finalize"})
    g.add_conditional_edges("classify", lambda s: "finalize" if s["fixed"] else s["route"],
                            {"cv_question": "answer_cv", "contact": "contact", "off_topic": "off_topic",
                             "finalize": "finalize"})
    for n in ("answer_cv", "contact", "off_topic"):
        g.add_edge(n, "finalize")
    g.add_edge("finalize", END)
    return g.compile()
