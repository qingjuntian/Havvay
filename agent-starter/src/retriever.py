"""Retriever backed by Qdrant via src.vector_store.VectorStore.

Behavior:
- Compute embedding for the query (OpenAI / Moonshot if keys present, else deterministic fallback)
- Query the Qdrant collection and return a list of formatted snippet strings (with source)
- If Qdrant or embeddings are unavailable, fall back to SAMPLE_DOCS
"""
from typing import List, Optional
import os
import hashlib
import json

try:
    import openai
except Exception:  # pragma: no cover - optional
    openai = None

from dotenv import load_dotenv

load_dotenv()

from .vector_store import VectorStore

SAMPLE_DOCS = [
    "Doc 1: Example knowledge about the product.",
    "Doc 2: Troubleshooting steps for the service.",
    "Doc 3: API reference highlights and examples.",
]

VECTOR_SIZE = 1536


def deterministic_embedding(text: str, size: int = VECTOR_SIZE) -> List[float]:
    h = hashlib.sha256(text.encode("utf-8")).digest()
    floats = [(b / 255.0) - 0.5 for b in h]
    reps = (size + len(floats) - 1) // len(floats)
    vec = (floats * reps)[:size]
    return [float(x) for x in vec]


def get_embedding(text: str) -> List[float]:
    # Prefer OPENAI key
    if openai is not None and os.getenv("OPENAI_API_KEY"):
        model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        try:
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            emb = client.embeddings.create(model=model, input=text).data[0].embedding
            if len(emb) != VECTOR_SIZE:
                if len(emb) < VECTOR_SIZE:
                    emb = emb + [0.0] * (VECTOR_SIZE - len(emb))
                else:
                    emb = emb[:VECTOR_SIZE]
            return [float(x) for x in emb]
        except Exception as exc:
            return deterministic_embedding(text)

    # Support MOONSHOT as OpenAI-compatible base
    if openai is not None and os.getenv("MOONSHOT_API_KEY"):
        base_url = os.getenv("MOONSHOT_API_BASE", "https://api.moonshot.cn/v1")
        model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        try:
            client = openai.OpenAI(api_key=os.getenv("MOONSHOT_API_KEY"), base_url=base_url)
            emb = client.embeddings.create(model=model, input=text).data[0].embedding
            if len(emb) != VECTOR_SIZE:
                if len(emb) < VECTOR_SIZE:
                    emb = emb + [0.0] * (VECTOR_SIZE - len(emb))
                else:
                    emb = emb[:VECTOR_SIZE]
            return [float(x) for x in emb]
        except Exception as exc:
            return deterministic_embedding(text)

    return deterministic_embedding(text)


class Retriever:
    def __init__(self, collection_name: Optional[str] = None):
        self.vs = None
        try:
            coll = collection_name or os.getenv("QDRANT_COLLECTION", "agent_docs")
            self.vs = VectorStore(collection_name=coll)
        except Exception as exc:
            # Qdrant not available — will fall back to SAMPLE_DOCS
            self.vs = None

    def retrieve(self, query: str, top_k: int = 3) -> List[str]:
        """Return a list of formatted snippets: 'Source: <path>\n<snippet>'"""
        # If no vector store, fall back
        if self.vs is None:
            return SAMPLE_DOCS[:top_k]

        try:
            emb = get_embedding(query)
            hits = self.vs.search_by_vector(emb, top_k=top_k)
            results = []
            for h in hits:
                payload = h.get("payload") or {}
                text = payload.get("text") or json.dumps(payload)
                source = payload.get("source") or payload.get("path") or h.get("id")
                formatted = f"Source: {source}\n{text}"
                results.append(formatted)
            if not results:
                return SAMPLE_DOCS[:top_k]
            return results
        except Exception as exc:
            return SAMPLE_DOCS[:top_k]
