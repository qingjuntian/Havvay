from src.agent import Agent
import os
from fastapi.testclient import TestClient
from src.memory import SessionMemory, LongTermMemory
from src.safety import SafetyLayer, UnsafePromptError
from src.main import app
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


def test_agent_stream_model_call_emits_chunks(monkeypatch):
    class FakeChunk:
        def __init__(self, text):
            self.choices = [type("Choice", (), {"delta": type("Delta", (), {"content": text})()})()]

    class FakeCompletions:
        def create(self, **kwargs):
            assert kwargs["stream"] is True
            return iter([FakeChunk("hello"), FakeChunk(" world")])

    class FakeClient:
        chat = type("Chat", (), {"completions": FakeCompletions()})()

    monkeypatch.setenv("MOONSHOT_API_KEY", "test-key")
    monkeypatch.setattr("src.agent.OpenAI", lambda **kwargs: FakeClient())

    chunks = []
    agent = Agent()
    response = agent.stream_model_call("hi", on_chunk=lambda chunk: chunks.append(chunk))

    assert response == "hello world"
    assert chunks == ["hello", " world"]


def test_openai_provider_uses_openai_configuration(monkeypatch):
    captured = {}

    class FakeClient:
        pass

    def build_client(**kwargs):
        captured.update(kwargs)
        return FakeClient()

    monkeypatch.setenv("MODEL_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test-key")
    monkeypatch.setenv("OPENAI_API_BASE", "https://example.test/v1")
    monkeypatch.setattr("src.agent.OpenAI", build_client)

    agent = Agent()
    assert agent._build_client().__class__ is FakeClient
    assert captured == {
        "api_key": "openai-test-key",
        "base_url": "https://example.test/v1",
    }
    assert agent._model_name() == "gpt-4o-mini"


def test_local_provider_reports_optional_dependency_requirement(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "local")
    monkeypatch.setenv("LOCAL_MODEL", "test/local-model")

    agent = Agent()
    try:
        agent.model_call("hello")
    except RuntimeError as exc:
        assert "transformers and torch" in str(exc)
    else:
        raise AssertionError("Expected local provider dependency error")


def test_query_stream_yields_sse_events(monkeypatch):
    class FakeChunk:
        def __init__(self, text):
            self.choices = [type("Choice", (), {"delta": type("Delta", (), {"content": text})()})()]

    class FakeCompletions:
        def create(self, **kwargs):
            assert kwargs["stream"] is True
            return iter([FakeChunk("hello"), FakeChunk(" world")])

    class FakeClient:
        chat = type("Chat", (), {"completions": FakeCompletions()})()

    monkeypatch.setenv("MOONSHOT_API_KEY", "test-key")
    monkeypatch.setattr("src.agent.OpenAI", lambda **kwargs: FakeClient())

    client = TestClient(app)
    response = client.post("/query/stream", json={"prompt": "hi", "session_id": "sse-test"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert '"status": "started"' in response.text
    assert '"status": "generating"' in response.text
    body = response.text
    assert "data: {\"type\": \"chunk\", \"content\": \"hello\"}" in body
    assert "data: {\"type\": \"chunk\", \"content\": \" world\"}" in body
    assert '"type": "final"' in body
    assert '"content": "hello world"' in body


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
