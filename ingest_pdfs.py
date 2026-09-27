"""
ingest_pdfs.py
Chunks the Lifespring Clinic PDFs and embeds them into a persistent
ChromaDB collection for the RAG agent.

Chunking approach — flatten first, then split by size:
  An earlier version tried to detect section boundaries via regex on
  physical PDF lines (e.g. "3. Billing Process" as its own line). That
  broke across environments: pypdf's line-break insertion during text
  extraction is version-dependent, so the same PDF produced clean
  single-line headings on one machine and headings fragmented across
  real newlines on another (e.g. "6." on one line, "Billing & Checkout"
  on the next), which either truncated/garbled the heading or — when the
  regex found zero valid headings because of this — fell through to a
  much looser fallback pattern that exploded into hundreds of one-word
  "sections" (module names, doctor surnames, stray capitalized words).

  This version sidesteps that entirely: all whitespace (spaces, tabs,
  newlines) is collapsed to single spaces before anything else happens,
  so chunking no longer depends on where pypdf happened to insert line
  breaks. Chunks are then built by size (~1000 chars, ~150 char overlap),
  preferring to break on sentence boundaries so a policy point doesn't
  get cut mid-sentence.

  Section labels in the metadata are still attempted (best-effort) by
  checking whether a chunk starts with something that looks like a short
  numbered heading — but if that detection ever misses, the chunk still
  gets embedded and indexed correctly; only the citation label is
  affected, not correctness of retrieval.

Usage:
    python ingest_pdfs.py --pdf_dir rag/ --persist_dir rag/chroma_db
"""

import argparse
import glob
import os
import re
from typing import List, Dict, Any

from pypdf import PdfReader
import chromadb
from chromadb.utils import embedding_functions

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

# Used only for best-effort section labeling on a chunk's leading text —
# not for finding chunk boundaries. A short "N. Title" with no spaced
# dash right after it (which would mark a nested process-step item like
# "1. Registration – Patient info collected...", not a real heading).
LEADING_HEADING_RE = re.compile(
    r'^(\d+\.\s+[^\u2013\u2014]{2,60}?)(?:\s\d+\.\s|\s[\u2013\u2014]\s|$)'
)


def extract_text(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    raw = "\n".join(page.extract_text() or "" for page in reader.pages)
    # Collapse ALL whitespace (including pypdf's version-dependent line
    # breaks) to single spaces. This is the fix: chunking below depends
    # only on character position and sentence punctuation, never on
    # where a newline happened to land.
    return re.sub(r'\s+', ' ', raw).strip()


def split_by_size(text: str, chunk_size: int = CHUNK_SIZE,
                   overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split flattened text into ~chunk_size pieces, preferring sentence
    boundaries so a chunk doesn't end mid-sentence when avoidable."""
    if len(text) <= chunk_size:
        return [text]

    sentences = re.split(r'(?<=[.!?])\s+', text)
    pieces, current = [], ""
    for sent in sentences:
        if len(current) + len(sent) + 1 <= chunk_size:
            current += (" " if current else "") + sent
        else:
            if current:
                pieces.append(current)
            if len(sent) > chunk_size:
                # a single sentence longer than the whole chunk budget —
                # hard-split on character boundary as a last resort
                for i in range(0, len(sent), chunk_size):
                    pieces.append(sent[i:i + chunk_size])
                current = ""
            else:
                current = sent
    if current:
        pieces.append(current)

    # add small overlap between consecutive pieces for retrieval continuity
    overlapped = []
    for i, p in enumerate(pieces):
        if i == 0:
            overlapped.append(p)
        else:
            tail = pieces[i - 1][-overlap:]
            overlapped.append(tail + " " + p)
    return overlapped


def guess_section_label(chunk_text: str) -> str:
    """Best-effort only — used for citation labels, not chunk boundaries.
    Falls back to a short excerpt if no clean heading pattern is found."""
    m = LEADING_HEADING_RE.match(chunk_text)
    if m:
        return m.group(1).strip()
    return chunk_text[:40].strip() + "..."


def chunk_document(text: str, doc_name: str) -> List[Dict[str, Any]]:
    pieces = split_by_size(text)
    doc_title = doc_name.replace(".pdf", "").replace("_", " ").title()
    return [
        {
            "doc": doc_name,
            "doc_title": doc_title,
            "section": guess_section_label(piece),
            "chunk_index": i,
            "text": piece,
        }
        for i, piece in enumerate(pieces)
    ]


def build_collection(pdf_dir: str, persist_dir: str,
                      collection_name: str = "lifespring_rag") -> None:
    client = chromadb.PersistentClient(path=persist_dir)

    # ChromaDB's built-in DefaultEmbeddingFunction runs a MiniLM model
    # via ONNX — no torch/sklearn/scipy dependency, fast first import.
    embed_fn = embedding_functions.DefaultEmbeddingFunction()

    # Fresh collection each run so re-running ingestion doesn't duplicate
    # chunks. Drop this if you want incremental ingestion instead.
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass
    collection = client.create_collection(
        name=collection_name, embedding_function=embed_fn
    )

    all_ids, all_docs, all_metadatas = [], [], []
    for pdf_path in sorted(glob.glob(os.path.join(pdf_dir, "*.pdf"))):
        doc_name = os.path.basename(pdf_path)
        text = extract_text(pdf_path)
        chunks = chunk_document(text, doc_name)

        print(f"{doc_name}: {len(chunks)} chunks")
        for k, c in enumerate(chunks):
            chunk_id = f"{doc_name}::{c['chunk_index']}"
            all_ids.append(chunk_id)
            all_docs.append(c["text"])
            all_metadatas.append({
                "doc": c["doc"],
                "doc_title": c["doc_title"],
                "section": c["section"],
            })

    collection.add(ids=all_ids, documents=all_docs, metadatas=all_metadatas)
    print(f"\nIngested {len(all_ids)} chunks into '{collection_name}' at {persist_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf_dir", default="rag/")
    parser.add_argument("--persist_dir", default="rag/chroma_db")
    parser.add_argument("--collection_name", default="lifespring_rag")
    args = parser.parse_args()

    build_collection(args.pdf_dir, args.persist_dir, args.collection_name)