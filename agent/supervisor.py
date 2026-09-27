"""
supervisor.py
Entry point for the Lifespring Agentic AI chatbot. A supervisor node
looks at the incoming query, decides which of the three sub-agents are
needed (RAG, NL2SQL, tool-calling — can be more than one), dispatches
to each, and — if more than one fired — merges their answers into one
coherent response.

Each sub-agent (rag_agent, nl2sql_agent, tool_calling_agent) is already
built and independently tested — this file only adds the routing,
merging, memory, and error-handling layers on top, via LangGraph.

Conversation memory: the graph is compiled with an InMemorySaver
checkpointer keyed by session_id (LangGraph's thread_id). Each turn's
{query, answer} is appended to state["history"] after answering, and
the last few turns are threaded into what the router and sub-agents
actually see — this is how "cancel that appointment" resolves against
an appointment booked in an earlier turn, without changing the
sub-agent functions themselves (they still just take a plain string;
the string just now carries recent context).

InMemorySaver only persists for the life of the process — restarting
supervisor.py loses all sessions. That's fine for local testing; a
Postgres/Redis checkpointer is the swap for production persistence,
same interface.

Multi-intent handling: a query like "is Dr. Kapoor free tomorrow, and
what does a consultation cost" genuinely needs two agents. The router
returns a LIST of routes (1-3 of rag/nl2sql/tool, or [] if none apply).
If exactly one route fires, its answer is returned as-is (no merge
call). If more than one fires, a merge step blends the separate
answers into one natural response.

Error handling: both the router call and each sub-agent call are
wrapped so a single failure (LLM API error, DB connection issue, etc)
degrades gracefully instead of crashing the whole turn — important
especially in the multi-intent case, where one agent failing shouldn't
take down the other's already-good answer.

Usage:
    python supervisor.py
"""

import os
import json
from typing import TypedDict, Literal, List, Dict

from groq import Groq
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver

from rag_agent import rag_agent
from nl2sql_agent import nl2sql_agent
from tool_calling_agent import tool_calling_agent

load_dotenv()

GROQ_MODEL = "openai/gpt-oss-120b"
_llm_client = Groq(api_key=os.environ["GROQ_API_KEY"])

Route = Literal["rag", "nl2sql", "tool"]
VALID_ROUTES = ("rag", "nl2sql", "tool")

AGENT_FUNCS = {
    "rag": rag_agent,
    "nl2sql": nl2sql_agent,
    "tool": tool_calling_agent,
}

HISTORY_TURNS_KEPT = 6  # last N {query, answer} turns threaded into context


class GraphState(TypedDict):
    query: str
    routes: List[Route]
    sub_answers: Dict[str, str]
    answer: str
    history: List[Dict[str, str]]  # [{"query": ..., "answer": ...}, ...]


ROUTER_SYSTEM_PROMPT = """You route a Lifespring Clinic user query to the
specialist agent(s) that can answer it. Respond with ONLY a JSON object
like {"routes": ["tool", "nl2sql"]} — no other text. The list can have
1 to 3 entries. If none apply, respond {"routes": []}.

Agents:
- "rag": questions answerable from the clinic's policy/info documents —
  billing process, insurance documents, pharmacy policy, emergency
  guidance, symptom guidance, follow-up care advice, consultation
  process, clinic services overview, doctor bios/specializations as
  DESCRIBED IN TEXT (not live schedule data).

- "nl2sql": questions that require looking up or aggregating REAL
  structured data already stored in the database — a specific
  patient's bills, a doctor's fee, medication stock counts, lab test
  history, counts/sums/filters over any table.

- "tool": requests to DO something — book or cancel an appointment,
  check a doctor's open slots for booking, check medicine availability
  for a purchase, send a notification. This also covers a follow-up
  like "cancel that appointment" or "book that slot" that refers back
  to something in the conversation history below.

Include MULTIPLE agents when a query has genuinely separate parts that
each need a different one. Do not add an agent whose info isn't
actually being asked for just because it's topically related.

An availability question ("is X free/available") is "tool" even though
the answer comes from the database, because the intent is booking-
adjacent action, not a data lookup.

You may be given recent conversation history before the current
message — use it only to resolve references ("that appointment", "her
fee") in the CURRENT message, not to answer something already answered.

If the query is small talk, off-topic, or too ambiguous to route
safely, respond {"routes": []}.
"""

UNCLEAR_ANSWER = (
    "I'm not sure how to help with that — I can answer questions about "
    "clinic policies, look up patient/doctor/billing data, or help book, "
    "cancel, or check availability for appointments. Could you rephrase?"
)


def build_contextualized_query(query: str, history: List[Dict[str, str]]) -> str:
    """Prepend recent turns so sub-agents can resolve references like
    "that appointment" without needing their own memory. If there's no
    history yet, just return the bare query unchanged."""
    if not history:
        return query

    transcript = "\n".join(
        f"User: {turn['query']}\nAssistant: {turn['answer']}" for turn in history
    )
    return (
        f"Previous conversation:\n{transcript}\n\n"
        f"Current message (answer only this, using the above only to "
        f"resolve references): {query}"
    )


def classify_routes(contextualized_query: str) -> List[Route]:
    try:
        response = _llm_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                {"role": "user", "content": contextualized_query},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
    except Exception:
        # Groq API error (timeout, rate limit, network) — fail safe to
        # "no routes", which surfaces as the unclear answer rather than
        # crashing the whole turn.
        return []

    try:
        parsed = json.loads(response.choices[0].message.content)
        raw_routes = parsed.get("routes", [])
    except (json.JSONDecodeError, AttributeError):
        raw_routes = []

    seen = set()
    routes = []
    for r in raw_routes:
        if r in VALID_ROUTES and r not in seen:
            routes.append(r)
            seen.add(r)
    return routes[:3]


def run_agent_safely(route: str, query: str) -> str:
    try:
        return AGENT_FUNCS[route](query)
    except Exception as e:
        # One sub-agent failing (DB down, tool exception, etc) shouldn't
        # crash the whole turn — especially matters in the multi-intent
        # case, where another agent's answer may still be good.
        return f"[I ran into an issue getting the {route} part of this answer: {e}]"


def merge_answers(query: str, sub_answers: Dict[str, str]) -> str:
    """Only called when 2+ agents fired. Blends separate answers into one
    coherent response instead of just concatenating them with headers."""
    parts = "\n\n".join(f"[{route} agent's answer]\n{ans}" for route, ans in sub_answers.items())
    try:
        response = _llm_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": (
                    "The user asked a question with multiple parts. Each part was "
                    "answered separately by a different specialist agent below. "
                    "Combine these into ONE natural, coherent response that "
                    "addresses everything the user asked — don't just concatenate "
                    "them or mention that multiple agents were involved."
                )},
                {"role": "user", "content": f"Original question: {query}\n\n{parts}"},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception:
        # Merge call itself failed — fall back to plain concatenation
        # rather than losing both sub-answers.
        return "\n\n".join(sub_answers.values())


# --- Graph nodes -----------------------------------------------------------

def supervisor_node(state: GraphState) -> GraphState:
    history = state.get("history", [])
    contextualized = build_contextualized_query(state["query"], history)
    routes = classify_routes(contextualized)
    return {**state, "routes": routes}


def dispatch_node(state: GraphState) -> GraphState:
    routes = state["routes"]
    history = state.get("history", [])
    contextualized = build_contextualized_query(state["query"], history)

    if not routes:
        final_answer = UNCLEAR_ANSWER
        sub_answers = {}
    else:
        sub_answers = {route: run_agent_safely(route, contextualized) for route in routes}
        if len(sub_answers) == 1:
            final_answer = next(iter(sub_answers.values()))
        else:
            final_answer = merge_answers(contextualized, sub_answers)

    new_history = (history + [{"query": state["query"], "answer": final_answer}])[-HISTORY_TURNS_KEPT:]

    return {**state, "sub_answers": sub_answers, "answer": final_answer, "history": new_history}


# --- Graph assembly ---------------------------------------------------------

def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("supervisor", supervisor_node)
    graph.add_node("dispatch", dispatch_node)

    graph.set_entry_point("supervisor")
    graph.add_edge("supervisor", "dispatch")
    graph.add_edge("dispatch", END)

    return graph.compile(checkpointer=InMemorySaver())


_compiled_graph = build_graph()


def chat(query: str, session_id: str = "default", return_debug: bool = False):
    # Only "query" goes in as input — NOT history/routes/etc. Those are
    # either freshly computed by the nodes each turn, or (for history)
    # left untouched so the checkpointer's persisted value carries over.
    # Passing history: [] here would silently wipe it every turn.
    config = {"configurable": {"thread_id": session_id}}
    result = _compiled_graph.invoke({"query": query}, config=config)
    if return_debug:
        return result
    return result["answer"]


if __name__ == "__main__":
    print("=== Single-turn tests ===")
    test_queries = [
        "What documents do I need for billing?",
        "What is Dr. Ayesha Kapoor's consultation fee?",
        "Is Dr. Ayesha Kapoor free on 2026-10-05, and what does a consultation with her cost?",
        "What's the capital of France?",
    ]
    for q in test_queries:
        print(f"\nQ: {q}")
        result = chat(q, session_id="single_turn_test", return_debug=True)
        print("Routes:", result["routes"])
        print("Answer:", result["answer"])

    print("\n\n=== Multi-turn follow-up test (separate session) ===")
    session = "followup_test"
    q1 = "Book patient P001 with doctor D001 on 2026-10-06 at 11:30, routine checkup"
    print(f"\nTurn 1 Q: {q1}")
    r1 = chat(q1, session_id=session, return_debug=True)
    print("Routes:", r1["routes"])
    print("Answer:", r1["answer"])

    q2 = "Actually, cancel that appointment"
    print(f"\nTurn 2 Q: {q2}")
    r2 = chat(q2, session_id=session, return_debug=True)
    print("Routes:", r2["routes"])
    print("Answer:", r2["answer"])