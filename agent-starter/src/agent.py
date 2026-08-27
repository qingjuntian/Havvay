"""Agent skeleton: orchestrates retriever + tools + model calls.
This is intentionally minimal — replace model_call() with your provider (OpenAI/HF/local).
"""
from typing import List
from .retriever import Retriever
from .tools import Tools

class Agent:
    def __init__(self):
        self.retriever = Retriever()
        self.tools = Tools()

    def model_call(self, prompt: str) -> str:
        # Placeholder: swap in real LLM invocation
        return f"[LLM simulated response to:] {prompt}"

    def run(self, prompt: str) -> str:
        # 1. retrieve context
        ctx = self.retriever.retrieve(prompt, top_k=3)
        # 2. assemble prompt
        full = """
Context:
{}

User:
{}
""".format("\n---\n".join(ctx), prompt)
        # 3. decide to call tools (simple heuristic)
        if "calculate" in prompt.lower():
            return self.tools.calc(prompt)
        # 4. call model
        return self.model_call(full)
