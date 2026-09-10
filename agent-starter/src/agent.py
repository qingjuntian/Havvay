"""Agent skeleton: orchestrates retriever + tools + model calls."""

from typing import Optional
import os

from dotenv import load_dotenv
from openai import OpenAI

from .retriever import Retriever
from .memory import SessionMemory
from .safety import SafetyLayer
from .tools import Tools

load_dotenv()


class Agent:
    def __init__(self, retriever=None, tools=None, memory=None, safety=None):
        self.retriever = retriever or Retriever()
        self.tools = tools or Tools()
        self.memory = memory or SessionMemory()
        self.safety = safety or SafetyLayer()

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

    def run(self, prompt: str, session_id: str = "default") -> str:
        prompt = self.safety.validate(prompt)
        history = self.memory.get(session_id)
        # 1. retrieve context
        ctx = self.retriever.retrieve(prompt, top_k=3)
        # 2. assemble prompt
        full = """
Context:
{}

User:
{}
""".format("\n---\n".join(ctx), prompt)
        if history:
            full = "Conversation history:\n{}\n\n{}".format(
                "\n".join(f"{turn['role']}: {turn['content']}" for turn in history),
                full,
            )
        # 3. decide to call tools (simple heuristic)
        if "calculate" in prompt.lower():
            response = self.tools.calc(prompt)
        else:
            # 4. call model
            response = self.model_call(full)
        self.memory.add(session_id, prompt, response)
        return response
