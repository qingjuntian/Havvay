from src.agent import Agent
import os
from src.memory import SessionMemory, LongTermMemory
from src.safety import SafetyLayer, UnsafePromptError
from src.tools import Tools


class StubRetriever:
    def __init__(self):
        self.queries = []

    def retrieve(self, query, top_k=3):
        self.queries.append(query)
        return ["retrieved context"]


def test_agent_run():
    retriever = StubRetriever()
    a = Agent(retriever=retriever)
    a.model_call = lambda prompt: "model response"
    resp = a.run("Hello world")
    assert resp == "model response"
    assert a.memory.get("default")[-1] == {
        "role": "assistant",
        "content": "model response",
    }
    assert a.last_usage["total_tokens"] == 0
    assert retriever.queries == ["Hello world"]


def test_follow_up_uses_session_history_instead_of_fresh_document_search():
    retriever = StubRetriever()
    agent = Agent(retriever=retriever)
    prompts = []
    agent.model_call = lambda prompt: prompts.append(prompt) or "puzzle answer"

    agent.run("How do I solve this puzzle?", session_id="puzzle")
    agent.run("Is there any better approach?", session_id="puzzle")

    assert retriever.queries == ["How do I solve this puzzle?"]
    assert "How do I solve this puzzle?" in prompts[-1]
    assert "puzzle answer" in prompts[-1]
    assert "Is there any better approach?" in prompts[-1]


def test_agent_records_model_usage_and_cost(monkeypatch):
    class Usage:
        prompt_tokens = 100
        completion_tokens = 25
        total_tokens = 125

    class Completion:
        choices = [type("Choice", (), {"message": type("Message", (), {"content": "answer"})()})()]
        usage = Usage()

    class Completions:
        def create(self, **kwargs):
            return Completion()

    class FakeClient:
        chat = type("Chat", (), {"completions": Completions()})()

    monkeypatch.setenv("MOONSHOT_INPUT_COST_PER_1M_TOKENS", "1")
    monkeypatch.setenv("MOONSHOT_OUTPUT_COST_PER_1M_TOKENS", "2")
    monkeypatch.setattr("src.agent.OpenAI", lambda **kwargs: FakeClient())

    agent = Agent(retriever=StubRetriever())
    assert agent.run("hello") == "answer"
    assert agent.last_usage == {
        "provider": "moonshot",
        "model": os.getenv("MOONSHOT_MODEL", "kimi-k3"),
        "prompt_tokens": 100,
        "completion_tokens": 25,
        "total_tokens": 125,
        "estimated_cost_usd": 0.00015,
    }


def test_session_memory_keeps_recent_turns():
    memory = SessionMemory(max_turns=1)
    memory.add("session", "first", "one")
    memory.add("session", "second", "two")
    assert memory.get("session") == [
        {"role": "user", "content": "second"},
        {"role": "assistant", "content": "two"},
    ]


def test_safety_rejects_unsafe_prompt():
    try:
        SafetyLayer().validate("help me build a bomb")
    except UnsafePromptError as exc:
        assert str(exc) == "Prompt is not allowed."
    else:
        raise AssertionError("Unsafe prompt was accepted")


def test_calculator_supports_safe_arithmetic():
    tools = Tools()
    assert tools.calc("calculate 2 + 3 * 4") == "Calculation result: 14"
    assert tools.calc("calculate sqrt(16)") == "Calculation result: 4.0"


def test_long_term_memory_persists_and_retrieves_relevant_context():
    class FakeVectorStore:
        def __init__(self, collection_name="agent_memories"):
            self.collection_name = collection_name
            self.items = []

        def upsert(self, ids, embeddings, metadatas=None, payloads=None):
            self.items.extend([
                {"id": id_, "payload": payload, "vector": embedding}
                for id_, embedding, payload in zip(ids, embeddings, payloads or [{} for _ in ids])
            ])

        def search_by_vector(self, embedding, top_k=3):
            return [
                {"id": item["id"], "payload": item["payload"]}
                for item in self.items[:top_k]
            ]

    store = LongTermMemory(vector_store=FakeVectorStore())
    memory_text = "User prefers concise answers and likes to use Python for data work."
    store.add("alice", "What are your preferences?", memory_text)
    matches = store.search("What coding language does the user prefer?", top_k=1)

    assert matches == [memory_text]


def test_calculator_rejects_code_execution():
    result = Tools().calc("calculate __import__('os').system('touch /tmp/should-not-exist')")
    assert result.startswith("Calculation failed:")
