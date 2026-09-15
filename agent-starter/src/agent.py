"""Agent skeleton: orchestrates retriever + tools + model calls."""

from typing import Optional, Callable
import os

from dotenv import load_dotenv
from openai import OpenAI

from .retriever import Retriever
from .memory import SessionMemory, LongTermMemory
from .safety import SafetyLayer
from .tools import Tools

load_dotenv()


class Agent:
    def __init__(self, retriever=None, tools=None, memory=None, safety=None, long_term_memory=None):
        self.retriever = retriever or Retriever()
        self.tools = tools or Tools()
        self.memory = memory or SessionMemory()
        self.long_term_memory = long_term_memory or LongTermMemory()
        self.safety = safety or SafetyLayer()
        self.last_usage = self._empty_usage()

    @staticmethod
    def _empty_usage():
        return {
            "provider": None,
            "model": None,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
        }

    @staticmethod
    def _usage_value(usage, name: str) -> int:
        if usage is None:
            return 0
        value = getattr(usage, name, None)
        if value is None and isinstance(usage, dict):
            value = usage.get(name)
        return int(value or 0)

    @staticmethod
    def _is_follow_up(prompt: str, history) -> bool:
        if not history:
            return False
        normalized = prompt.lower().strip()
        follow_up_phrases = (
            "better approach",
            "another approach",
            "another way",
            "what about",
            "what if",
            "why",
            "how about",
            "can you explain",
            "continue",
            "more details",
        )
        return len(normalized.split()) <= 12 and any(
            phrase in normalized for phrase in follow_up_phrases
        )

    def _build_client(self):
        provider = os.getenv("MODEL_PROVIDER", "moonshot").lower()
        if provider == "local":
            return None

        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("OPENAI_API_BASE")
        else:
            api_key = (
                os.getenv("MOONSHOT_API_KEY")
                or os.getenv("KIMI_API_KEY")
                or os.getenv("KIMIAPIKEY")
            )
            base_url = os.getenv("MOONSHOT_API_BASE", "https://api.moonshot.cn/v1")

        if not api_key:
            raise RuntimeError(
                f"Missing API key for MODEL_PROVIDER={provider}. Configure the provider's API key in the environment."
            )

        client_options = {"api_key": api_key}
        if base_url:
            client_options["base_url"] = base_url
        return OpenAI(**client_options)

    @staticmethod
    def _provider() -> str:
        return os.getenv("MODEL_PROVIDER", "moonshot").lower()

    @staticmethod
    def _model_name() -> str:
        provider = Agent._provider()
        if provider == "local":
            return os.getenv("LOCAL_MODEL", "google/flan-t5-small")
        if provider == "openai":
            return os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        return os.getenv("MOONSHOT_MODEL", "kimi-k3")

    @staticmethod
    def _local_model_call(prompt: str) -> str:
        try:
            from transformers import pipeline
        except ImportError as exc:
            raise RuntimeError(
                "Local model support requires optional dependencies. Install transformers and torch."
            ) from exc

        generator = pipeline("text2text-generation", model=Agent._model_name())
        result = generator(prompt, max_new_tokens=int(os.getenv("LOCAL_MAX_NEW_TOKENS", "256")))
        return result[0].get("generated_text", "") if result else ""

    def _update_usage_from_response(self, usage, model_name: str):
        prompt_tokens = self._usage_value(usage, "prompt_tokens")
        completion_tokens = self._usage_value(usage, "completion_tokens")
        total_tokens = self._usage_value(usage, "total_tokens") or prompt_tokens + completion_tokens
        input_rate = float(os.getenv("MOONSHOT_INPUT_COST_PER_1M_TOKENS", "0"))
        output_rate = float(os.getenv("MOONSHOT_OUTPUT_COST_PER_1M_TOKENS", "0"))
        self.last_usage = {
            "provider": "moonshot",
            "model": model_name,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": (
                prompt_tokens * input_rate + completion_tokens * output_rate
            ) / 1_000_000,
        }

    def model_call(self, prompt: str) -> str:
        if self._provider() == "local":
            self.last_usage = self._empty_usage()
            self.last_usage["provider"] = "local"
            self.last_usage["model"] = self._model_name()
            return self._local_model_call(prompt)

        client = self._build_client()
        model_name = self._model_name()

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
        self._update_usage_from_response(getattr(completion, "usage", None), model_name)
        return content or ""

    def iter_model_stream(self, prompt: str):
        if self._provider() == "local":
            self.last_usage = self._empty_usage()
            self.last_usage["provider"] = "local"
            self.last_usage["model"] = self._model_name()
            yield self._local_model_call(prompt)
            return

        client = self._build_client()
        model_name = self._model_name()
        final_usage = None

        try:
            stream = client.chat.completions.create(
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
                stream=True,
            )
            for chunk in stream:
                if not getattr(chunk, "choices", None):
                    final_usage = getattr(chunk, "usage", None)
                    continue
                delta = chunk.choices[0].delta
                content = getattr(delta, "content", None)
                if content:
                    yield content
                if getattr(chunk, "usage", None) is not None:
                    final_usage = chunk.usage
        except Exception as exc:  # pragma: no cover - network / service errors should surface clearly
            raise RuntimeError(f"Moonshot streaming API call failed: {exc}") from exc
        self._update_usage_from_response(final_usage, model_name)

    def stream_model_call(self, prompt: str, on_chunk: Optional[Callable[[str], None]] = None) -> str:
        chunks = []
        for chunk in self.iter_model_stream(prompt):
            chunks.append(chunk)
            if on_chunk is not None:
                on_chunk(chunk)
        return "".join(chunks)

    def run(self, prompt: str, session_id: str = "default") -> str:
        prompt = self.safety.validate(prompt)
        self.last_usage = self._empty_usage()
        history = self.memory.get(session_id)
        is_follow_up = self._is_follow_up(prompt, history)
        long_term_ctx = self.long_term_memory.search(prompt, top_k=2)
        # 1. retrieve context
        ctx = [] if is_follow_up else self.retriever.retrieve(prompt, top_k=3)
        # 2. assemble prompt
        memory_block = "\n---\n".join(long_term_ctx) if long_term_ctx else "No relevant long-term memory found."
        full = """
Long-term memory (use only when relevant):
{}

Document context (use only when relevant):
{}

Current user message:
{}
""".format(memory_block, "\n---\n".join(ctx), prompt)
        if history:
            full = """Conversation history (primary context for this follow-up):
{}

{}

Answer the current message as a continuation of the conversation. Do not replace
the conversation topic with document context unless the user explicitly asks about
the documents.
""".format(
                "\n".join(f"{turn['role']}: {turn['content']}" for turn in history),
                full,
            )
        # 3. decide to call tools (simple heuristic)
        if "calculate" in prompt.lower():
            response = self.tools.calc(prompt)
            self.last_usage = self._empty_usage()
        else:
            # 4. call model
            response = self.model_call(full)
        self.memory.add(session_id, prompt, response)
        self.long_term_memory.add(session_id, prompt, response)
        return response
