"""Small planner/executor boundary for multi-step agent work."""

from dataclasses import dataclass, field
import re
from typing import List, Optional

from .safety import SafetyLayer


@dataclass(frozen=True)
class PlanStep:
    """One executable action produced by the planner."""

    id: str
    action: str
    input: str
    tool: Optional[str] = None


@dataclass
class ExecutionResult:
    """Observable result of executing a plan."""

    response: str
    steps: List[PlanStep] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)


class Planner:
    """Decompose a user task into safe, currently supported actions.

    This first planner is deliberately deterministic. It makes the plan
    inspectable and keeps tool selection separate from tool execution; a model
    backed planner can replace ``plan`` without changing the executor contract.
    """

    def __init__(self, safety=None):
        self.safety = safety or SafetyLayer()

    def plan(self, task: str) -> List[PlanStep]:
        task = self.safety.validate(task)
        clauses = [clause.strip() for clause in re.split(r"\s+(?:and then|then)\s+|\n+", task, flags=re.IGNORECASE) if clause.strip()]
        steps = []
        for index, clause in enumerate(clauses, start=1):
            normalized = clause.lower()
            if "calculate" in normalized:
                steps.append(PlanStep(f"step-{index}", "tool", clause, "calc"))
            elif any(term in normalized for term in ("search", "look up", "find online", "web")):
                steps.append(PlanStep(f"step-{index}", "tool", clause, "search_web"))
            else:
                steps.append(PlanStep(f"step-{index}", "respond", clause))
        return steps


class Executor:
    """Execute planner steps through the existing agent tool/model boundary."""

    def __init__(self, agent, tools=None, safety=None):
        self.agent = agent
        self.tools = tools or agent.tools
        self.safety = safety or agent.safety

    def execute(self, steps: List[PlanStep], session_id: str = "default") -> ExecutionResult:
        if not steps:
            raise ValueError("Plan must contain at least one step.")

        outputs = []
        for step in steps:
            validated_input = self.safety.validate(step.input)
            if step.action == "respond" and outputs:
                validated_input = (
                    f"{validated_input}\n\n"
                    f"Previous step output:\n{outputs[-1]}"
                )
            if step.action == "tool":
                if step.tool == "calc":
                    output = self.tools.calc(validated_input)
                elif step.tool == "search_web":
                    output = self.tools.search_web(validated_input)
                else:
                    raise ValueError(f"Unsupported tool: {step.tool}")
            elif step.action == "respond":
                output = self.agent.run(validated_input, session_id=session_id)
            else:
                raise ValueError(f"Unsupported plan action: {step.action}")
            outputs.append(output)
            if step.action == "tool":
                memory = getattr(self.agent, "memory", None)
                if memory is not None:
                    memory.add(session_id, validated_input, output)
                long_term_memory = getattr(self.agent, "long_term_memory", None)
                if long_term_memory is not None:
                    long_term_memory.add(session_id, validated_input, output)

        response = outputs[0] if len(outputs) == 1 else "\n\n".join(outputs)
        return ExecutionResult(response=response, steps=list(steps), outputs=outputs)


class PlannerExecutor:
    """Convenience facade that exposes both the plan and its result."""

    def __init__(self, agent, planner=None, executor=None):
        self.planner = planner or Planner(safety=agent.safety)
        self.executor = executor or Executor(agent)

    def run(self, task: str, session_id: str = "default") -> ExecutionResult:
        steps = self.planner.plan(task)
        return self.executor.execute(steps, session_id=session_id)