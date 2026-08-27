"""Simple retriever stub. Replace with Qdrant / Weaviate / Pinecone integration.
"""
from typing import List

SAMPLE_DOCS = [
    "Doc 1: Example knowledge about the product.",
    "Doc 2: Troubleshooting steps for the service.",
    "Doc 3: API reference highlights and examples.",
]

class Retriever:
    def __init__(self):
        # In a real implementation connect to your vector DB here
        pass

    def retrieve(self, query: str, top_k: int = 3) -> List[str]:
        # naive stub: return sample docs
        return SAMPLE_DOCS[:top_k]
