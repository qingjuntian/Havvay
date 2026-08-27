"""Agent skeleton: orchestrates retriever + tools + model calls."""

from typing import Optional
import os

from dotenv import load_dotenv
from openai import OpenAI

from .retriever import Retriever
from .tools import Tools

load_dotenv()


class Agent:
    def __init__(self):
        self.retriever = Retriever()
        self.tools = Tools()

    def model_call(self, prompt: str) -> str:
        api_key = (
            os.getenv("MOONSHOT_API_KEY")
            or os.getenv("KIMI_API_KEY")
            or os.getenv("KIMIAPIKEY")
        )
        if not api_key:
            raise RuntimeError(
                "Missing Moonshot API key. Set MOONSHOT_API_KEY, KIMI_API_KEY, or KIMIAPIKEY in the environment or .env."
            )

        client = OpenAI(
            api_key=api_key,
            base_url="https://api.moonshot.cn/v1",
        )

        model_name = os.getenv("MOONSHOT_MODEL", "kimi-k3")

        try:
            completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。"
                            "你会为用户提供安全、有帮助、准确的回答。"
                            "Moonshot AI 为专有名词，不可翻译成其他语言。"
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )
        except Exception as exc:  # pragma: no cover - network / service errors should surface clearly
            raise RuntimeError(f"Moonshot API call failed: {exc}") from exc

        content: Optional[str] = completion.choices[0].message.content
        return content or ""

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
