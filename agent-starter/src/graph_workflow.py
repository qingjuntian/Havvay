"""LangGraph-based workflow orchestration (Phase 2, Week 7 evaluation).

One assistant workflow demonstrating capabilities the deterministic planner
(`src/planner.py`) cannot express:

- Branching: prompts are classified into a direct model-answer path or a
  tool-execution path via conditional edges.
- Retry policy: the model-answer node loops back on itself (a graph cycle)
  until the call succeeds or the attempt budget is exhausted.
- Human approval: tool execution is gated behind an interrupt; the run pauses
  until a caller approves or rejects the pending action.
- Persisted state: a shared SQLite checkpointer keeps interrupted runs
  resumable across process restarts, keyed by `thread_id`.

Graphs are compiled per request (cheap) but share one `SqliteSaver`
checkpointer, so approval state survives restarts. Pinned to the langgraph
0.0.x API (`set_entry_point`, `interrupt_before`) for compatibility with the
project's pydantic v1 / FastAPI 0.99 stack; see ADR-002.
"""

import operator
import os
from typing import Annotated, Callable, Optional, TypedDict

from langgraph.graph import END, StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver

DEFAULT_CHECKPOINT_DB = "data/langgraph_checkpoints.sqlite"

COMPOSE_PROMPT = (
    "The user asked: {prompt}\n"
    "The '{tool}' tool returned:\n"
    "{tool_output}\n"
    "Write a concise final answer that incorporates the tool result."
)

REJECTED_RESPONSE = (
    "Tool execution was rejected by a human reviewer. "
    "No tool was run; ask again without the tool request or request approval."
)


class WorkflowState(TypedDict, total=False):
    prompt: str
    session_id: str
    route: str  # "tool" | "answer"
    tool: Optional[str]  # "calc" | "search_web"
    approved: Optional[bool]
    attempts: int
    error: Optional[str]
    tool_output: Optional[str]
    response: str
    log: Annotated[list, operator.add]


def _classify(prompt: str) -> str:
    normalized = prompt.strip().lower()
    if normalized.startswith(("calculate", "calc")):
        return "tool"
    if "search" in normalized or "look up" in normalized:
        return "tool"
    return "answer"


def describe_pending(values: dict) -> dict:
    """Describe the action waiting on human approval for API responses."""
    return {
        "node": "human_gate",
        "action": "execute tool '%s'" % values.get("tool"),
        "prompt": values.get("prompt"),
    }


def build_graph(
    model_call: Callable[[str], str],
    tools,
    checkpointer=None,
    interrupt_before=(),
    max_attempts: Optional[int] = None,
):
    """Compile the assistant workflow graph.

    Args:
        model_call: Callable taking a prompt string and returning text. Must
            raise ``RuntimeError`` on provider failure (``Agent.model_call``
            satisfies this).
        tools: Object exposing ``calc(prompt)`` and ``search_web(query)``.
        checkpointer: LangGraph checkpointer; required when interrupts or
            resume are used.
        interrupt_before: Node names to pause before (e.g. ``["human_gate"]``).
        max_attempts: Total model-call attempts before falling back. Defaults
            to ``LANGGRAPH_MAX_MODEL_ATTEMPTS`` or 2.
    """
    if max_attempts is None:
        max_attempts = max(1, int(os.getenv("LANGGRAPH_MAX_MODEL_ATTEMPTS", "2")))

    def classify(state: WorkflowState) -> dict:
        route = _classify(state["prompt"])
        tool = None
        if route == "tool":
            normalized = state["prompt"].lower()
            tool = "calc" if normalized.startswith(("calculate", "calc")) else "search_web"
        return {"route": route, "tool": tool, "log": [f"classify -> {route}"]}

    def human_gate(state: WorkflowState) -> dict:
        # Never executed on the API path: the graph interrupts before this
        # node and the resume call writes `approved` via update_state. Runs
        # without interrupts pass `approved` in the initial state instead.
        return {"log": ["human_gate passed"]}

    def execute_tool(state: WorkflowState) -> dict:
        tool = state.get("tool") or "search_web"
        try:
            if tool == "calc":
                output = tools.calc(state["prompt"])
            else:
                output = tools.search_web(state["prompt"])
        except Exception as exc:
            return {
                "error": f"tool '{tool}' failed: {exc}",
                "log": [f"execute_tool({tool}) failed: {exc}"],
            }
        return {
            "tool_output": output,
            "error": None,
            "log": [f"execute_tool({tool}) ok"],
        }

    def compose(state: WorkflowState) -> dict:
        prompt = COMPOSE_PROMPT.format(
            prompt=state["prompt"],
            tool=state.get("tool"),
            tool_output=state.get("tool_output", ""),
        )
        try:
            response = model_call(prompt)
        except RuntimeError as exc:
            return {"error": str(exc), "log": [f"compose failed: {exc}"]}
        return {"response": response, "error": None, "log": ["compose ok"]}

    def answer(state: WorkflowState) -> dict:
        attempts = state.get("attempts", 0) + 1
        try:
            response = model_call(state["prompt"])
        except RuntimeError as exc:
            return {
                "attempts": attempts,
                "error": str(exc),
                "log": [f"answer attempt {attempts} failed: {exc}"],
            }
        return {
            "attempts": attempts,
            "response": response,
            "error": None,
            "log": [f"answer ok on attempt {attempts}"],
        }

    def fallback(state: WorkflowState) -> dict:
        attempts = state.get("attempts", 0)
        response = (
            "Model unavailable after %d attempt(s): %s"
            % (attempts, state.get("error", "unknown error"))
        )
        return {"response": response, "log": ["fallback response"]}

    def rejected(state: WorkflowState) -> dict:
        return {"response": REJECTED_RESPONSE, "log": ["tool execution rejected"]}

    def route_after_classify(state: WorkflowState) -> str:
        return state["route"]

    def route_after_gate(state: WorkflowState) -> str:
        return "execute_tool" if state.get("approved") else "rejected"

    def route_after_answer(state: WorkflowState) -> str:
        if not state.get("error"):
            return "done"
        if state.get("attempts", 0) < max_attempts:
            return "retry"
        return "fallback"

    def route_after_effect(state: WorkflowState) -> str:
        return "fallback" if state.get("error") else "done"

    builder = StateGraph(WorkflowState)
    builder.add_node("classify", classify)
    builder.add_node("human_gate", human_gate)
    builder.add_node("execute_tool", execute_tool)
    builder.add_node("compose", compose)
    builder.add_node("answer", answer)
    builder.add_node("fallback", fallback)
    builder.add_node("rejected", rejected)

    builder.set_entry_point("classify")
    builder.add_conditional_edges(
        "classify", route_after_classify, {"tool": "human_gate", "answer": "answer"}
    )
    builder.add_conditional_edges(
        "human_gate", route_after_gate, {"execute_tool": "execute_tool", "rejected": "rejected"}
    )
    builder.add_edge("execute_tool", "compose")
    builder.add_conditional_edges(
        "compose", route_after_effect, {"fallback": "fallback", "done": END}
    )
    builder.add_conditional_edges(
        "answer",
        route_after_answer,
        {"retry": "answer", "fallback": "fallback", "done": END},
    )
    builder.add_edge("fallback", END)
    builder.add_edge("rejected", END)

    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=list(interrupt_before) or None,
    )


_CHECKPOINTER = None


def default_checkpointer():
    """Shared process-wide SQLite checkpointer (survives restarts on disk)."""
    global _CHECKPOINTER
    if _CHECKPOINTER is None:
        db_path = os.getenv("LANGGRAPH_CHECKPOINT_DB", DEFAULT_CHECKPOINT_DB)
        _CHECKPOINTER = SqliteSaver.from_conn_string(db_path)
    return _CHECKPOINTER


def reset_default_checkpointer():
    """Reset the shared checkpointer (used by tests)."""
    global _CHECKPOINTER
    _CHECKPOINTER = None
