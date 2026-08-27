from src.agent import Agent


def test_agent_run():
    a = Agent()
    resp = a.run("Hello world")
    assert isinstance(resp, str)
    assert "Hello world" in resp or "LLM simulated response" in resp
