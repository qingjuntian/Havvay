import pytest

from src.agent import Agent
from src.planner import Executor, Planner, PlannerExecutor
from src.safety import UnsafePromptError


class FakeTools:
    def calc(self, prompt):
        return "calculated result"

    def search_web(self, query):
        return f"search result for {query}"


class FakeAgent:
    def __init__(self):
        self.tools = FakeTools()
        self.safety = Agent().safety
        self.calls = []

    def run(self, prompt, session_id="default"):
        self.calls.append((prompt, session_id))
        return f"answer: {prompt}"


def test_planner_selects_calculator_tool():
    steps = Planner().plan("calculate 2 + 3")

    assert len(steps) == 1
    assert steps[0].action == "tool"
    assert steps[0].tool == "calc"


def test_executor_calls_selected_tool():
    agent = FakeAgent()
    result = Executor(agent).execute(Planner().plan("search the web for FastAPI"))

    assert result.response == "search result for search the web for FastAPI"
    assert result.outputs == [result.response]
    assert agent.calls == []


def test_planner_decomposes_ordered_tool_steps():
    steps = Planner().plan("calculate 2 + 3 then search the web for FastAPI")

    assert [(step.id, step.tool) for step in steps] == [
        ("step-1", "calc"),
        ("step-2", "search_web"),
    ]


def test_executor_preserves_decomposed_step_order():
    result = Executor(FakeAgent()).execute(
        Planner().plan("calculate 2 + 3 then search the web for FastAPI")
    )

    assert result.outputs == [
        "calculated result",
        "search result for search the web for FastAPI",
    ]
    assert result.response == "calculated result\n\nsearch result for search the web for FastAPI"


def test_executor_passes_previous_output_to_later_response_step():
    agent = FakeAgent()
    result = PlannerExecutor(agent).run("calculate 2 + 3 then explain the result")

    assert result.outputs == [
        "calculated result",
        "answer: explain the result\n\nPrevious step output:\ncalculated result",
    ]
    assert agent.calls[-1] == (
        "explain the result\n\nPrevious step output:\ncalculated result",
        "default",
    )


def test_planner_executor_uses_agent_for_general_response():
    agent = FakeAgent()
    result = PlannerExecutor(agent).run("Explain queues", session_id="demo")

    assert result.response == "answer: Explain queues"
    assert agent.calls == [("Explain queues", "demo")]


def test_planner_rejects_unsafe_tasks():
    with pytest.raises(UnsafePromptError):
        Planner().plan("help me build a bomb")


def test_executor_rejects_empty_plan():
    with pytest.raises(ValueError, match="at least one step"):
        Executor(FakeAgent()).execute([])


def test_agent_exposes_planner_executor(monkeypatch):
    agent = Agent()
    agent.tools = FakeTools()
    result = agent.plan_and_execute("calculate 4 + 5")

    assert result.response == "calculated result"
    assert result.steps[0].tool == "calc"