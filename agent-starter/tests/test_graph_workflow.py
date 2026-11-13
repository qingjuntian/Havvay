"""Tests for the LangGraph workflow (src/graph_workflow.py) and its API."""

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.sqlite import SqliteSaver

import src.main as main_module
from src.main import app
from src import graph_workflow
from src.graph_workflow import build_graph

from tests.test_api import FakeAgent, FakeTools


class RecordingTools(FakeTools):
    def __init__(self):
        self.calc_calls = []
        self.search_calls = []

    def calc(self, prompt):
        self.calc_calls.append(prompt)
        return "Calculation result: 4"

    def search_web(self, query):
        self.search_calls.append(query)
        return f"search results for: {query} (stub)"


def ok_model(prompt):
    return f"model answer to: {prompt[:40]}"


def flaky_model_factory(failures):
    calls = {"count": 0}

    def model(prompt):
        calls["count"] += 1
        if calls["count"] <= failures:
            raise RuntimeError(f"provider error {calls['count']}")
        return f"recovered after {calls['count']} attempts"

    return model, calls


def always_failing_model(prompt):
    raise RuntimeError("provider down")


def test_direct_answer_branch_skips_tool_and_gate():
    tools = RecordingTools()
    graph = build_graph(ok_model, tools)

    result = graph.invoke({"prompt": "what is FastAPI", "log": [], "attempts": 0})

    assert result["response"] == "model answer to: what is FastAPI"
    assert result["attempts"] == 1
    assert tools.calc_calls == [] and tools.search_calls == []
    assert result["log"] == ["classify -> answer", "answer ok on attempt 1"]


def test_model_retry_recovers_within_attempt_budget():
    model, calls = flaky_model_factory(failures=2)
    graph = build_graph(model, RecordingTools(), max_attempts=3)

    result = graph.invoke({"prompt": "hello there", "log": [], "attempts": 0})

    assert result["response"] == "recovered after 3 attempts"
    assert result["attempts"] == 3
    assert calls["count"] == 3
    assert "answer attempt 1 failed: provider error 1" in result["log"]
    assert "answer attempt 2 failed: provider error 2" in result["log"]


def test_model_retry_exhaustion_uses_fallback():
    graph = build_graph(always_failing_model, RecordingTools(), max_attempts=2)

    result = graph.invoke({"prompt": "hello there", "log": [], "attempts": 0})

    assert result["attempts"] == 2
    assert "Model unavailable after 2 attempt(s)" in result["response"]
    assert "provider down" in result["response"]
    assert result["log"][-1] == "fallback response"


def test_tool_branch_pauses_for_approval_then_runs_on_approve():
    tools = RecordingTools()
    checkpointer = SqliteSaver.from_conn_string(":memory:")
    graph = build_graph(
        ok_model, tools, checkpointer=checkpointer, interrupt_before=["human_gate"]
    )
    config = {"configurable": {"thread_id": "approve-run"}}

    graph.invoke(
        {"prompt": "calculate 2 + 2", "log": [], "attempts": 0, "approved": None},
        config,
    )
    snapshot = graph.get_state(config)

    assert snapshot.next == ("human_gate",)
    assert tools.calc_calls == []
    pending = graph_workflow.describe_pending(snapshot.values)
    assert pending["node"] == "human_gate"
    assert "calc" in pending["action"]

    graph.update_state(config, {"approved": True, "log": ["human approved"]}, as_node="human_gate")
    graph.invoke(None, config)
    snapshot = graph.get_state(config)

    assert snapshot.next == ()
    assert tools.calc_calls == ["calculate 2 + 2"]
    assert "Calculation result: 4" in snapshot.values["response"] or \
        "model answer to:" in snapshot.values["response"]
    assert "execute_tool(calc) ok" in snapshot.values["log"]


def test_tool_branch_rejection_skips_tool():
    tools = RecordingTools()
    checkpointer = SqliteSaver.from_conn_string(":memory:")
    graph = build_graph(
        ok_model, tools, checkpointer=checkpointer, interrupt_before=["human_gate"]
    )
    config = {"configurable": {"thread_id": "reject-run"}}

    graph.invoke(
        {"prompt": "search for qdrant docs", "log": [], "attempts": 0, "approved": None},
        config,
    )
    graph.update_state(config, {"approved": False, "log": ["human rejected"]}, as_node="human_gate")
    graph.invoke(None, config)
    snapshot = graph.get_state(config)

    assert snapshot.next == ()
    assert tools.search_calls == []
    assert "rejected by a human reviewer" in snapshot.values["response"]
    assert "tool execution rejected" in snapshot.values["log"]


def test_interrupted_run_survives_graph_rebuild(tmp_path):
    """Checkpoint persistence: resume with a fresh checkpointer on the same DB."""
    db = str(tmp_path / "checkpoints.sqlite")
    tools = RecordingTools()

    graph1 = build_graph(
        ok_model, tools,
        checkpointer=SqliteSaver.from_conn_string(db),
        interrupt_before=["human_gate"],
    )
    config = {"configurable": {"thread_id": "restart-run"}}
    graph1.invoke(
        {"prompt": "calculate 6 * 7", "log": [], "attempts": 0, "approved": None},
        config,
    )
    assert graph1.get_state(config).next == ("human_gate",)

    # Simulate a process restart: new checkpointer + newly compiled graph.
    graph2 = build_graph(
        ok_model, tools,
        checkpointer=SqliteSaver.from_conn_string(db),
        interrupt_before=["human_gate"],
    )
    snapshot = graph2.get_state(config)
    assert snapshot.next == ("human_gate",)

    graph2.update_state(config, {"approved": True, "log": ["human approved"]}, as_node="human_gate")
    graph2.invoke(None, config)
    snapshot = graph2.get_state(config)

    assert snapshot.next == ()
    assert tools.calc_calls == ["calculate 6 * 7"]
    assert "compose ok" in snapshot.values["log"]


# --- API coverage -----------------------------------------------------------


class WorkflowFakeAgent(FakeAgent):
    def __init__(self, model=None):
        super().__init__()
        self._model = model or ok_model
        self.tools = RecordingTools()

    def model_call(self, prompt):
        return self._model(prompt)


@pytest.fixture
def workflow_api(monkeypatch, tmp_path):
    agent = WorkflowFakeAgent()
    monkeypatch.setattr(main_module, "agent", agent)
    monkeypatch.setenv("LANGGRAPH_CHECKPOINT_DB", str(tmp_path / "api.sqlite"))
    graph_workflow.reset_default_checkpointer()
    yield agent
    graph_workflow.reset_default_checkpointer()


def test_workflow_endpoint_direct_answer(workflow_api):
    response = TestClient(app).post(
        "/query/workflow",
        json={"prompt": "what is uvicorn", "session_id": "wf-direct"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["response"] == "model answer to: what is uvicorn"
    assert body["session_id"] == "wf-direct"
    assert body["thread_id"]
    assert body["trace"] == ["classify -> answer", "answer ok on attempt 1"]


def test_workflow_endpoint_pauses_and_resumes_on_approval(workflow_api):
    client = TestClient(app)
    start = client.post(
        "/query/workflow",
        json={"prompt": "calculate 10 / 4", "session_id": "wf-tool"},
    )

    assert start.status_code == 202
    pending = start.json()
    assert pending["status"] == "awaiting_approval"
    assert pending["pending"]["node"] == "human_gate"
    assert "calc" in pending["pending"]["action"]
    assert workflow_api.tools.calc_calls == []

    resume = client.post(
        f"/query/workflow/{pending['thread_id']}/resume",
        json={"approved": True, "session_id": "wf-tool"},
    )

    assert resume.status_code == 200
    body = resume.json()
    assert workflow_api.tools.calc_calls == ["calculate 10 / 4"]
    assert "model answer to:" in body["response"]
    assert "human approved" in body["trace"]


def test_workflow_endpoint_resume_rejects_tool(workflow_api):
    client = TestClient(app)
    start = client.post(
        "/query/workflow",
        json={"prompt": "search the web for FastAPI", "session_id": "wf-reject"},
    )
    assert start.status_code == 202

    resume = client.post(
        f"/query/workflow/{start.json()['thread_id']}/resume",
        json={"approved": False, "session_id": "wf-reject"},
    )

    assert resume.status_code == 200
    assert "rejected by a human reviewer" in resume.json()["response"]
    assert workflow_api.tools.search_calls == []


def test_workflow_resume_unknown_thread_returns_404(workflow_api):
    response = TestClient(app).post(
        "/query/workflow/does-not-exist/resume",
        json={"approved": True},
    )

    assert response.status_code == 404
