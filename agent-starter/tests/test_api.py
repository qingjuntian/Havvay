import json

from fastapi.testclient import TestClient

from src.main import app
import src.main as main_module


class FakeSafety:
    def validate(self, prompt):
        return prompt.strip()


class FakeMemory:
    def get(self, session_id):
        return []

    def add(self, session_id, prompt, response):
        return None


class FakeLongTermMemory:
    def search(self, prompt, top_k=2):
        return []

    def add(self, session_id, prompt, response):
        return None


class FakeRetriever:
    def retrieve(self, prompt, top_k=3):
        return []


class FakeTools:
    def calc(self, prompt):
        return "calculated"


class FakeAgent:
    @staticmethod
    def _is_follow_up(prompt, history):
        return False

    def __init__(self):
        self.safety = FakeSafety()
        self.memory = FakeMemory()
        self.long_term_memory = FakeLongTermMemory()
        self.retriever = FakeRetriever()
        self.tools = FakeTools()
        self.last_usage = {
            "provider": "test",
            "model": "fake-model",
            "prompt_tokens": 1,
            "completion_tokens": 2,
            "total_tokens": 3,
            "estimated_cost_usd": 0.0,
        }

    def run(self, prompt, session_id="default"):
        return f"answer to {prompt}"

    def _empty_usage(self):
        return {
            "provider": None,
            "model": None,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
        }

    def iter_model_stream(self, prompt):
        yield "streamed"
        yield " answer"


def test_health_endpoint():
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_query_endpoint_uses_agent_without_external_services(monkeypatch):
    monkeypatch.setattr(main_module, "agent", FakeAgent())

    response = TestClient(app).post(
        "/query",
        json={"prompt": "hello", "session_id": "api-test"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "response": "answer to hello",
        "session_id": "api-test",
        "usage": main_module.agent.last_usage,
    }


def test_query_stream_endpoint_returns_sse_events(monkeypatch):
    monkeypatch.setattr(main_module, "agent", FakeAgent())

    response = TestClient(app).post(
        "/query/stream",
        json={"prompt": "hello", "session_id": "api-stream-test"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = [
        json.loads(line.removeprefix("data: "))
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    assert events[0] == {"type": "status", "status": "started"}
    assert {"type": "chunk", "content": "streamed"} in events
    assert {"type": "chunk", "content": " answer"} in events
    assert events[-1]["type"] == "final"
    assert events[-1]["content"] == "streamed answer"