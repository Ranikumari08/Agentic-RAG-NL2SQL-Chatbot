"""
app.py
FastAPI wrapper around the LangGraph supervisor (agent/supervisor.py).
This is the single entry point for the whole Lifespring Agentic AI
chatbot — everything built so far (RAG agent, NL2SQL agent, tool-calling
agent, multi-intent routing, conversation memory) is reachable through
this one /chat endpoint.

Run from the project root (Lifespring_Agentic_AI/), not from inside
agent/ — the sys.path setup below and the agents' own relative paths
(rag/chroma_db, tools/.env) all assume the working directory is the
project root:

    uvicorn app:app --reload

Then POST to http://127.0.0.1:8000/chat with a JSON body like:
    {"message": "What documents do I need for billing?", "session_id": "abc123"}

Interactive API docs are auto-generated at http://127.0.0.1:8000/docs
"""

import os
import sys
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# agent/ holds supervisor.py, which itself does bare imports like
# "from rag_agent import rag_agent" — those only resolve if agent/ is on
# sys.path, which happens automatically when you run `python agent/x.py`
# directly but NOT when importing it as a module from the project root
# (which is what running this API does). This line replicates that
# script-execution sys.path behavior so supervisor.py and its sibling
# agent files work unchanged, with no import refactor needed.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agent"))
from supervisor import chat  # noqa: E402

app = FastAPI(
    title="Lifespring Agentic AI",
    description="Supervisor-routed RAG + NL2SQL + tool-calling clinic assistant",
    version="1.0",
)

# Permissive CORS for local development / demoing against any frontend.
# Tighten allow_origins to your actual frontend's URL before deploying
# this anywhere it isn't just you testing locally.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="The user's message")
    session_id: str | None = Field(
        None,
        description=(
            "Groups messages into one conversation for memory/follow-up "
            "resolution (e.g. 'cancel that appointment'). Omit to get a "
            "fresh random session id each call — you generally want to "
            "generate one per user session and reuse it across a chat."
        ),
    )


class ChatResponse(BaseModel):
    answer: str
    routes: list[str]
    session_id: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())

    try:
        result = chat(req.message, session_id=session_id, return_debug=True)
    except Exception as e:
        # Supervisor already handles sub-agent/router failures gracefully
        # internally — reaching here means something truly unexpected
        # happened (e.g. Groq API key missing/invalid). Surface it as a
        # proper HTTP error rather than a raw stack trace.
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

    return ChatResponse(
        answer=result["answer"],
        routes=result.get("routes", []),
        session_id=session_id,
    )