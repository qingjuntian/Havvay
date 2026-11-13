from threading import Event

import pytest

from src.multi_agent import MultiAgentCoordinator
from src.safety import SafetyLayer


class FakeTools:
    def __init__(self):
        self.first_started = Event()

    def calc(self, prompt):
        if "1 + 1" in prompt:
            self.first_started.set()
            assert self.first_started.wait(timeout=1)
            return "2"
        if "2 + 2" in prompt:
            assert self.first_started.wait(timeout=1)
            return "4"
        if "fail" in prompt:
            raise RuntimeError("worker failed")
        return "calculated"

    def search_web(self, query):
        return f"search result for {query}"


class FakeAgent:
    def __init__(self):
        self.tools = FakeTools()
        self.safety = SafetyLayer()
        self.calls = []
        self.memory = None
        self.long_term_memory = None

    def run(self, prompt, session_id="default"):
        self.calls.append((prompt, session_id))
        return f"answer: {prompt}"


def test_coordinator_aggregates_parallel_tool_results_in_plan_order():
    agent = FakeAgent()
    result = MultiAgentCoordinator(agent, max_workers=2).run(
        "calculate 1 + 1 then calculate 2 + 2"
    )

    assert result.outputs == ["2", "4"]
    assert result.response == "2\n\n4"


def test_coordinator_passes_prior_tool_result_to_agent_step():
    agent = FakeAgent()
    result = MultiAgentCoordinator(agent).run(
        "search the web for FastAPI then summarize the result",
        session_id="coordinator-test",
    )

    assert result.outputs[0] == "search result for search the web for FastAPI"
    assert agent.calls == [
        (
            "summarize the result\n\nPrevious step output:\n"
            "search result for search the web for FastAPI",
            "coordinator-test",
        )
    ]


def test_coordinator_propagates_worker_failure():
    with pytest.raises(RuntimeError, match="worker failed"):
        MultiAgentCoordinator(FakeAgent()).run("calculate fail")


def test_agent_exposes_opt_in_multi_agent_execution():
    from src.agent import Agent

    agent = Agent(tools=FakeTools(), safety=SafetyLayer())
    result = agent.multi_agent_plan_and_execute("calculate 3 + 4")

    assert result.outputs == ["calculated"]