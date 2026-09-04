"""
Minimal VectorStore wrapper for Qdrant.
- Upsert documents with precomputed embeddings
- Search by embedding

This is intentionally small and defensive: if Qdrant is not reachable, it raises clear errors and the retriever falls back to the sample docs.
"""
import os
from typing import List, Dict, Optional

import numpy as np

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as rest
except Exception:  # pragma: no cover - dependency/runtime
    QdrantClient = None
    rest = None


class VectorStore:
    def __init__(self, collection_name: str = "agent_docs"):
        if QdrantClient is None:
            raise RuntimeError("qdrant-client is not installed in the environment")

        qdrant_url = os.getenv("QDRANT_URL")
        if qdrant_url:
            # expect form http(s)://host:port
            # qdrant-client accepts host/port or url depending on version; fall back to simple ctor
            client_args = {"url": qdrant_url}
        else:
            # Use the numeric loopback address to avoid local DNS/proxy issues.
            client_args = {"host": os.getenv("QDRANT_HOST", "127.0.0.1"), "port": int(os.getenv("QDRANT_PORT", 6333))}

        # Create QdrantClient while disabling httpx trust_env to avoid system proxy interference when possible
        try:
            self.client = QdrantClient(**{**client_args, "check_compatibility": False, "httpx_client_params": {"trust_env": False}})
        except TypeError:
            # older qdrant-client versions may not accept httpx_client_params
            self.client = QdrantClient(**{**client_args, "check_compatibility": False})
        self.collection_name = collection_name

        # create collection if not exists
        try:
            existing = []
            try:
                # Some qdrant server responses can be transiently unavailable; retry a few times
                cols = None
                for attempt in range(3):
                    try:
                        cols = self.client.get_collections()
                        break
                    except Exception as exec:
                        import time
                        time.sleep(0.5 * (attempt + 1))
                existing = [c.name for c in getattr(cols, "collections", [])] if cols is not None else []
            except Exception as exec:
                existing = []

            if collection_name not in existing:
                # Prefer client APIs when available
                try:
                    if hasattr(self.client, "recreate_collection"):
                        self.client.recreate_collection(
                            collection_name=collection_name,
                            vector_size=1536,
                            distance=rest.Distance.COSINE,
                        )
                    else:
                        self.client.create_collection(collection_name=collection_name, vectors_config=rest.VectorParams(size=1536, distance=rest.Distance.COSINE))
                except Exception as exc:
                    # Some client-server combinations may cause httpx/httpcore RemoteProtocolError
                    # Fall back to a plain HTTP PUT to /collections/{name} which works on many qdrant versions
                    try:
                        import httpx
                        qdrant_url = os.getenv("QDRANT_URL")
                        if not qdrant_url:
                            host = os.getenv("QDRANT_HOST", "localhost")
                            port = int(os.getenv("QDRANT_PORT", 6333))
                            qdrant_url = f"http://{host}:{port}"
                        url = f"{qdrant_url.rstrip('/')}/collections/{collection_name}"
                        payload = {"vectors": {"size": 1536, "distance": "Cosine"}}
                        # disable environment proxy resolution to avoid platform/system proxy interfering (trust_env=False)
                        r = httpx.put(url, json=payload, timeout=10.0, trust_env=False)
                        if r.status_code not in (200, 201):
                            raise RuntimeError(f"HTTP create collection failed: {r.status_code} {r.text}")
                    except Exception as exc:  # pragma: no cover
                        raise RuntimeError(f"Failed to create or access qdrant collection: {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"Failed to create or access qdrant collection: {exc}") from exc

    def upsert(self, ids: List[str], embeddings: List[List[float]], metadatas: Optional[List[Dict]] = None, payloads: Optional[List[Dict]] = None):
        # embeddings: list of lists (floats)
        if len(ids) != len(embeddings):
            raise ValueError("ids and embeddings length mismatch")
        payloads = payloads or [{} for _ in ids]
        try:
            # Qdrant requires point IDs to be unsigned integers or UUID strings.
            # Convert any non-integer-like id to a stable UUID using uuid5.
            import uuid

            converted_ids = []
            for orig_id in ids:
                # If it's an int string, keep as int
                try:
                    int_id = int(orig_id)
                    if int_id >= 0:
                        converted_ids.append(int_id)
                        continue
                except Exception:
                    pass
                # If it's a valid UUID, keep the string
                try:
                    uuid_obj = uuid.UUID(str(orig_id))
                    converted_ids.append(str(uuid_obj))
                    continue
                except Exception:
                    pass
                # Otherwise, create a stable UUID5 from the string
                uuid_obj = uuid.uuid5(uuid.NAMESPACE_URL, str(orig_id))
                converted_ids.append(str(uuid_obj))

            points = [rest.PointStruct(id=i, vector=list(vec), payload=payload or {}) for i, vec, payload in zip(converted_ids, embeddings, payloads)]
            self.client.upsert(collection_name=self.collection_name, points=points)
        except Exception as exc:
            raise RuntimeError(f"Qdrant upsert failed: {exc}") from exc

    def search_by_vector(self, embedding: List[float], top_k: int = 3) -> List[Dict]:
        try:
            if hasattr(self.client, "search"):
                hits = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=embedding,
                    limit=top_k,
                )
            else:
                response = self.client.query_points(
                    collection_name=self.collection_name,
                    query=embedding,
                    limit=top_k,
                    with_payload=True,
                )
                hits = response.points
            # hits are PointStruct objects — convert to simple dicts
            results = []
            for h in hits:
                results.append({
                    "id": str(h.id),
                    "score": float(h.score) if hasattr(h, "score") else None,
                    "payload": getattr(h, "payload", {})
                })
            return results
        except Exception as exc:
            raise RuntimeError(f"Qdrant search failed: {exc}") from exc
