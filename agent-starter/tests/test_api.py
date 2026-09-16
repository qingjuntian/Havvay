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
        yield "streamed Chinese: 中文"
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


def test_query_endpoint_queues_long_running_prompt(monkeypatch):
    monkeypatch.setattr(main_module, "agent", FakeAgent())
    main_module.task_queue.worker = lambda prompt, session_id: main_module.agent.run(
        prompt, session_id=session_id
    )

    response = TestClient(app).post(
        "/query",
        json={
            "prompt": "Process all files in the background and generate a full report",
            "session_id": "long-running-test",
        },
    )

    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert response.json()["execution_mode"] == "background"
    assert response.json()["session_id"] == "long-running-test"
    assert response.json()["task_id"]


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
    assert "中文" in response.text
    assert "\\u4e2d" not in response.text
    assert {"type": "chunk", "content": "streamed Chinese: 中文"} in events
    assert {"type": "chunk", "content": " answer"} in events
    assert events[-1]["type"] == "final"
    assert events[-1]["content"] == "streamed Chinese: 中文 answer"


def test_query_stream_endpoint_queues_long_running_prompt(monkeypatch):
    monkeypatch.setattr(main_module, "agent", FakeAgent())
    main_module.task_queue.worker = lambda prompt, session_id: main_module.agent.run(
        prompt, session_id=session_id
    )

    response = TestClient(app).post(
        "/query/stream",
        json={
            "prompt": "Process all files in the background and generate a full report",
            "session_id": "long-stream-test",
        },
    )

    events = [
        json.loads(line.removeprefix("data: "))
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]

    assert response.status_code == 200
    assert events[0] == {"type": "status", "status": "started"}
    assert any(event.get("status") == "queued" for event in events)
    assert any(event.get("status") == "running" for event in events)
    assert events[-1]["type"] == "final"
    assert events[-1]["content"] == (
        "answer to Process all files in the background and generate a full report"
    )


def test_task_endpoints_process_batch_in_background(monkeypatch):
    monkeypatch.setattr(main_module, "agent", FakeAgent())
    main_module.task_queue.worker = lambda prompt, session_id: main_module.agent.run(
        prompt, session_id=session_id
    )
    client = TestClient(app)

    response = client.post(
        "/tasks",
        json={"prompts": ["first", "second"], "session_id": "batch-test"},
    )

    assert response.status_code == 202
    task_id = response.json()["task_id"]
    assert response.json()["status"] == "queued"

    for _ in range(20):
        status = client.get(f"/tasks/{task_id}")
        if status.json()["status"] == "completed":
            break

    assert status.status_code == 200
    assert status.json()["status"] == "completed"
    assert status.json()["completed"] == 2
    assert [item["response"] for item in status.json()["results"]] == [
        "answer to first",
        "answer to second",
    ]


def test_task_submission_rejects_empty_batch():
    response = TestClient(app).post("/tasks", json={"prompts": ["", "  "]})

    assert response.status_code == 422


def test_task_status_returns_not_found():
    response = TestClient(app).get("/tasks/does-not-exist")

    assert response.status_code == 404