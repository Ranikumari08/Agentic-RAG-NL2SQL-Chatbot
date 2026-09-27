"""
rag_agent.py
Standalone RAG agent: embed query -> retrieve top-k chunks from the
ChromaDB collection built by ingest_pdfs.py -> generate a grounded
answer. Exposes a single rag_agent(query) function so this can be
tested in isolation before the supervisor calls it as a sub-agent.

Run ingest_pdfs.py once before using this.
"""

import os
import chromadb
from chromadb.utils import embedding_functions
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Free, open-weight models via Groq (no credit card, no payment).
# Model names on Groq's free tier shift over time — check
# console.groq.com for the current list before relying on this one.
GROQ_MODEL = "openai/gpt-oss-120b"
_llm_client = Groq(api_key=os.environ["GROQ_API_KEY"])

PERSIST_DIR = "rag/chroma_db"
COLLECTION_NAME = "lifespring_rag"
TOP_K = 4

SYSTEM_PROMPT = """You are the RAG agent for Lifespring Clinic's assistant.
Answer ONLY using the provided context chunks. If the context doesn't
contain the answer, say so plainly instead of guessing. Keep answers
concise and cite which document/section the info came from when useful.
Never provide medical diagnosis — for symptom or treatment questions,
give the clinic's stated guidance and note when a doctor visit is advised.
"""

_client = chromadb.PersistentClient(path=PERSIST_DIR)
# Must match the embedding function used in ingest_pdfs.py, or
# retrieval will silently produce garbage similarity scores.
_embed_fn = embedding_functions.DefaultEmbeddingFunction()
_collection = _client.get_collection(COLLECTION_NAME, embedding_function=_embed_fn)


def retrieve(query: str, top_k: int = TOP_K):
    results = _collection.query(query_texts=[query], n_results=top_k)
    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        chunks.append({
            "text": doc,
            "doc": meta["doc"],
            "section": meta["section"],
            "score": 1 - dist,  # cosine distance -> similarity
        })
    return chunks


def build_context(chunks) -> str:
    parts = []
    for c in chunks:
        parts.append(f"[{c['doc']} — {c['section']}]\n{c['text']}")
    return "\n\n---\n\n".join(parts)


def generate_answer(query: str, context: str) -> str:
    response = _llm_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"},
        ],
        temperature=0.2,  # keep it grounded/factual, not creative
    )
    return response.choices[0].message.content


def rag_agent(query: str, top_k: int = TOP_K, return_debug: bool = False):
    chunks = retrieve(query, top_k=top_k)

    if not chunks or max(c["score"] for c in chunks) < 0.2:
        answer = (
            "I don't have information on that in the clinic documents I have "
            "access to. You may want to contact the clinic directly."
        )
    else:
        context = build_context(chunks)
        answer = generate_answer(query, context)

    if return_debug:
        return {"answer": answer, "retrieved": chunks}
    return answer


if __name__ == "__main__":
    test_queries = [
        "What documents do I need for billing?",
        "What should I do if I have a severe allergic reaction?",
        "What are Dr. Priya Nair's consultation hours?",
    ]
    for q in test_queries:
        print(f"\nQ: {q}")
        result = rag_agent(q, return_debug=True)
        print("Retrieved sections:", [(c["doc"], c["section"], round(c["score"], 3)) for c in result["retrieved"]])
        print(result["answer"])