"""
Index local text/markdown files into Qdrant via src.vector_store.VectorStore.

Usage:
  python scripts/index_docs.py --dir data/docs --batch-size 64

Behavior:
- Walks the directory for .txt and .md files
- Splits files into overlapping chunks (by characters)
- Uses OpenAI-compatible embeddings if OPENAI_API_KEY or MOONSHOT_API_KEY is present
  - If MOONSHOT_API_KEY is present, sets OPENAI api_base to Moonshot's base URL
- Falls back to a deterministic hashed embedding if no embedding key available
- Upserts vectors and payloads into Qdrant collection 'agent_docs' (vector_size=1536)

Note: set QDRANT_HOST/PORT or QDRANT_URL environment variables to connect to Qdrant.
"""

import os
import sys
import argparse
import glob
import json
import hashlib
from typing import List, Tuple, Iterator

try:
    import openai
except Exception:  # pragma: no cover - optional
    openai = None

from dotenv import load_dotenv

load_dotenv()

from src.vector_store import VectorStore

VECTOR_SIZE = 1536
DEFAULT_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Simple character-based chunking with overlap."""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end]
        chunks.append(chunk)
        if end == len(text):
            break
        start = max(end - overlap, end - overlap)
    return chunks


def deterministic_embedding(text: str, size: int = VECTOR_SIZE) -> List[float]:
    """Deterministic pseudo-embedding based on SHA256; values in [-0.5,0.5]."""
    h = hashlib.sha256(text.encode("utf-8")).digest()
    # convert bytes to floats in [0,1), then map to [-0.5,0.5]
    floats = [(b / 255.0) - 0.5 for b in h]
    # repeat to reach desired size
    reps = (size + len(floats) - 1) // len(floats)
    vec = (floats * reps)[:size]
    return [float(x) for x in vec]


def get_embedding(text: str) -> List[float]:
    """Try provider embeddings, fall back to deterministic."""
    if openai is not None and os.getenv("OPENAI_API_KEY"):
        model = os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
        try:
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            emb = client.embeddings.create(model=model, input=text).data[0].embedding
            if len(emb) != VECTOR_SIZE:
                # If embedding size differs, pad or trim
                if len(emb) < VECTOR_SIZE:
                    emb = emb + [0.0] * (VECTOR_SIZE - len(emb))
                else:
                    emb = emb[:VECTOR_SIZE]
            return [float(x) for x in emb]
        except Exception as exc:  # pragma: no cover - runtime
            print(f"OpenAI embedding failed: {exc}", file=sys.stderr)
            print("Falling back to deterministic embeddings", file=sys.stderr)
            return deterministic_embedding(text)

    # Support MOONSHOT as OpenAI-compatible base if provided
    if openai is not None and os.getenv("MOONSHOT_API_KEY"):
        # Moonshot OpenAI-compat base
        base_url = os.getenv("MOONSHOT_API_BASE", "https://api.moonshot.cn/v1")
        model = os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
        try:
            client = openai.OpenAI(api_key=os.getenv("MOONSHOT_API_KEY"), base_url=base_url)
            emb = client.embeddings.create(model=model, input=text).data[0].embedding
            if len(emb) != VECTOR_SIZE:
                if len(emb) < VECTOR_SIZE:
                    emb = emb + [0.0] * (VECTOR_SIZE - len(emb))
                else:
                    emb = emb[:VECTOR_SIZE]
            return [float(x) for x in emb]
        except Exception as exc:  # pragma: no cover - runtime
            print(f"Moonshot embedding failed: {exc}", file=sys.stderr)
            print("Falling back to deterministic embeddings", file=sys.stderr)
            return deterministic_embedding(text)

    # final fallback
    return deterministic_embedding(text)


def iter_files(doc_dir: str) -> Iterator[str]:
    patterns = ["**/*.txt", "**/*.md"]
    for pat in patterns:
        for path in glob.glob(os.path.join(doc_dir, pat), recursive=True):
            yield path


def read_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except Exception:
        # try latin-1 as fallback
        with open(path, "r", encoding="latin-1") as fh:
            return fh.read()


def index_directory(doc_dir: str, batch_size: int = 64):
    vs = VectorStore(collection_name=os.getenv("QDRANT_COLLECTION", "agent_docs"))

    docs_indexed = 0
    batch_ids = []
    batch_embs = []
    batch_payloads = []

    for file_path in iter_files(doc_dir):
        text = read_file(file_path)
        chunks = chunk_text(text)
        for i, chunk in enumerate(chunks):
            doc_id = f"{os.path.basename(file_path)}::{i}"
            emb = get_embedding(chunk)
            payload = {"text": chunk, "source": file_path}
            batch_ids.append(doc_id)
            batch_embs.append(emb)
            batch_payloads.append(payload)

            if len(batch_ids) >= batch_size:
                vs.upsert(ids=batch_ids, embeddings=batch_embs, payloads=batch_payloads)
                docs_indexed += len(batch_ids)
                print(f"Upserted {len(batch_ids)} chunks, total indexed: {docs_indexed}")
                batch_ids = []
                batch_embs = []
                batch_payloads = []

    # flush remaining
    if batch_ids:
        vs.upsert(ids=batch_ids, embeddings=batch_embs, payloads=batch_payloads)
        docs_indexed += len(batch_ids)
        print(f"Upserted {len(batch_ids)} chunks, total indexed: {docs_indexed}")

    print(f"Indexing complete. Total chunks indexed: {docs_indexed}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default="data/docs", help="Directory containing docs to index (default: data/docs)")
    parser.add_argument("--batch-size", type=int, default=64, help="Batch size for upserts")
    args = parser.parse_args()

    if not os.path.isdir(args.dir):
        print(f"Docs directory not found: {args.dir}", file=sys.stderr)
        sys.exit(2)

    index_directory(args.dir, batch_size=args.batch_size)


if __name__ == "__main__":
    main()
