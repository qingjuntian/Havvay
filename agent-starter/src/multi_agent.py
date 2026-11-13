"""Prototype planner-to-worker coordination with ordered result aggregation."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import List, Optional
from uuid import uuid4

from .planner import ExecutionResult, PlanStep, Planner


@dataclass(frozen=True)
class WorkerMessage:
    run_id: str
    step: PlanStep
    session_id: str
    previous_output: Optional[str] = None


@dataclass(frozen=True)
class WorkerResult:
    run_id: str
    step_id: str
    output: Optional[str] = None
    error: Optional[Exception] = None


class StepWorker:
    """Execute one planned tool or agent step and return its message result."""

    def __init__(self, agent):
        self.agent = agent
        self.tools = agent.tools
        self.safety = agent.safety

    def execute(self, message: WorkerMessage) -> WorkerResult:
        try:
            step_input = self.safety.validate(message.step.input)
            if message.step.action == "respond":
                if message.previous_output is not None:
                    step_input = (
                        f"{step_input}\n\nPrevious step output:\n"
                        f"{message.previous_output}"
                    )
                output = self.agent.run(step_input, session_id=message.session_id)
            elif message.step.action == "tool":
                if message.step.tool == "calc":
                    output = self.tools.calc(step_input)
                elif message.step.tool == "search_web":
                    output = self.tools.search_web(step_input)
                else:
                    raise ValueError(f"Unsupported tool: {message.step.tool}")
            else:
                raise ValueError(f"Unsupported plan action: {message.step.action}")
            return WorkerResult(message.run_id, message.step.id, output=output)
        except Exception as exc:
            return WorkerResult(message.run_id, message.step.id, error=exc)


class ResultAggregator:
    """Validate worker messages and assemble outputs in planner order."""

    def aggregate(
        self, steps: List[PlanStep], messages: List[WorkerMessage], results: List[WorkerResult]
    ) -> ExecutionResult:
        messages_by_step = {message.step.id: message for message in messages}
        results_by_step = {}
        for result in results:
            if result.step_id not in messages_by_step:
                raise ValueError(f"Unexpected worker result for step: {result.step_id}")
            if result.step_id in results_by_step:
                raise ValueError(f"Duplicate worker result for step: {result.step_id}")
            if result.run_id != messages_by_step[result.step_id].run_id:
                raise ValueError(f"Worker result run ID mismatch for step: {result.step_id}")
            results_by_step[result.step_id] = result

        outputs = []
        for step in steps:
            result = results_by_step.get(step.id)
            if result is None:
                raise ValueError(f"Missing worker result for step: {step.id}")
            if result.error is not None:
                raise result.error
            outputs.append(result.output or "")

        response = outputs[0] if len(outputs) == 1 else "\n\n".join(outputs)
        return ExecutionResult(response=response, steps=list(steps), outputs=outputs)


class MultiAgentCoordinator:
    """Dispatch independent tool steps to workers and aggregate in plan order."""

    def __init__(self, agent, planner=None, worker=None, max_workers: int = 4):
        self.agent = agent
        self.planner = planner or Planner(safety=agent.safety)
        self.worker = worker or StepWorker(agent)
        self.max_workers = max(1, max_workers)
        self.aggregator = ResultAggregator()

    def run(self, task: str, session_id: str = "default") -> ExecutionResult:
        steps = self.planner.plan(task)
        if not steps:
            raise ValueError("Plan must contain at least one step.")

        run_id = str(uuid4())
        messages: List[WorkerMessage] = []
        results: List[WorkerResult] = []
        step_index = 0
        previous_output = None

        while step_index < len(steps):
            step = steps[step_index]
            if step.action == "tool":
                end_index = step_index
                while end_index < len(steps) and steps[end_index].action == "tool":
                    end_index += 1
                batch = [
                    WorkerMessage(run_id, item, session_id)
                    for item in steps[step_index:end_index]
                ]
                messages.extend(batch)
                with ThreadPoolExecutor(
                    max_workers=min(self.max_workers, len(batch)),
                    thread_name_prefix="agent-worker",
                ) as executor:
                    batch_results = list(executor.map(self.worker.execute, batch))

                for message, result in zip(batch, batch_results):
                    if result.error is not None:
                        raise result.error
                    if message.step.action == "tool":
                        if memory := getattr(self.agent, "memory", None):
                            memory.add(session_id, message.step.input, result.output or "")
                        if long_term_memory := getattr(self.agent, "long_term_memory", None):
                            long_term_memory.add(session_id, message.step.input, result.output or "")
                    previous_output = result.output
                    results.append(result)
                step_index = end_index
                continue

            message = WorkerMessage(run_id, step, session_id, previous_output)
            messages.append(message)
            result = self.worker.execute(message)
            if result.error is not None:
                raise result.error
            previous_output = result.output
            results.append(result)
            step_index += 1

        return self.aggregator.aggregate(steps, messages, results)