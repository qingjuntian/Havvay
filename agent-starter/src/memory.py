from collections import defaultdict
from threading import Lock
from typing import Dict, List, Optional
import hashlib
import os


def deterministic_embedding(text: str, size: int = 1536) -> List[float]:
    h = hashlib.sha256(text.encode("utf-8")).digest()
    floats = [(b / 255.0) - 0.5 for b in h]
    reps = (size + len(floats) - 1) // len(floats)
    vec = (floats * reps)[:size]
    return [float(x) for x in vec]


class SessionMemory:
    """Small in-memory conversation store for a single application process."""

    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        self._sessions: Dict[str, List[Dict[str, str]]] = defaultdict(list)
        self._lock = Lock()

    def get(self, session_id: str) -> List[Dict[str, str]]:
        with self._lock:
            return list(self._sessions.get(session_id, []))

    def add(self, session_id: str, prompt: str, response: str) -> None:
        with self._lock:
            turns = self._sessions[session_id]
            turns.extend([
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": response},
            ])
            self._sessions[session_id] = turns[-self.max_turns * 2:]


class LongTermMemory:
    """Persistent memory layer stored in Qdrant, with an in-memory fallback."""

    def __init__(self, vector_store=None, collection_name: Optional[str] = None):
        self._lock = Lock()
        self._fallback: List[str] = []
        self.vector_store = vector_store
        self.collection_name = collection_name or os.getenv("QDRANT_MEMORY_COLLECTION", "agent_memories")

    def _get_vector_store(self):
        if self.vector_store is not None:
            return self.vector_store
        try:
            from .vector_store import VectorStore

            self.vector_store = VectorStore(collection_name=self.collection_name)
            return self.vector_store
        except Exception:
            self.vector_store = None
            return None

    @staticmethod
    def _summarize(prompt: str, response: str) -> str:
        prompt = (prompt or "").strip()
        response = (response or "").strip()
        if response:
            return response
        if prompt:
            return prompt
        return ""

    def add(self, session_id: str, prompt: str, response: str) -> str:
        memory_text = self._summarize(prompt, response)
        if not memory_text:
            return ""

        embedding = self._embedding(memory_text)
        with self._lock:
            vector_store = self._get_vector_store()
            if vector_store is not None:
                try:
                    point_id = f"{session_id}:{len(self._fallback)}"
                    vector_store.upsert(
                        ids=[point_id],
                        embeddings=[embedding],
                        payloads=[{"text": memory_text, "session_id": session_id, "type": "conversation_memory"}],
                    )
                    return memory_text
                except Exception:
                    self.vector_store = None
            self._fallback.append(memory_text)
        return memory_text

    def _embedding(self, text: str) -> List[float]:
        try:
            from .retriever import get_embedding

            return get_embedding(text)
        except Exception:
            return deterministic_embedding(text)

    def search(self, query: str, top_k: int = 3) -> List[str]:
        if not query:
            return []

        embedding = self._embedding(query)
        with self._lock:
            vector_store = self._get_vector_store()
            if vector_store is not None:
                try:
                    hits = vector_store.search_by_vector(embedding, top_k=top_k)
                    results: List[str] = []
                    for hit in hits:
                        payload = hit.get("payload") or {}
                        text = payload.get("text") or str(payload)
                        if text not in results:
                            results.append(text)
                    if results:
                        return results[:top_k]
                except Exception:
                    self.vector_store = None

            candidates = [item for item in self._fallback if query.lower() in item.lower() or item.lower() in query.lower()]
            if not candidates:
                candidates = self._fallback[-top_k:]
            return candidates[:top_k]
