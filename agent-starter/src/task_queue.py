"""Small in-process background queue for long-running agent tasks."""

from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import Dict, List
from uuid import uuid4


def is_long_running_prompt(prompt: str) -> bool:
    """Return whether a prompt explicitly describes work suited to a queue."""
    normalized = " ".join(prompt.lower().split())
    indicators = (
        "in the background",
        "run in background",
        "process all",
        "analyze all",
        "across all files",
        "generate a full report",
        "run overnight",
        "long-running",
        "long running",
    )
    return any(indicator in normalized for indicator in indicators)


class TaskQueue:
    def __init__(self, worker=None):
        self.worker = worker
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="agent-task")
        self._tasks: Dict[str, Dict] = {}
        self._lock = Lock()

    def submit(self, prompts: List[str], session_id: str = "default") -> str:
        task_id = str(uuid4())
        task = {
            "task_id": task_id,
            "status": "queued",
            "session_id": session_id,
            "total": len(prompts),
            "completed": 0,
            "results": [],
            "error": None,
        }
        with self._lock:
            self._tasks[task_id] = task
        self._executor.submit(self._run, task_id, list(prompts), session_id)
        return task_id

    def get(self, task_id: str):
        with self._lock:
            task = self._tasks.get(task_id)
            return dict(task) if task is not None else None

    def _run(self, task_id: str, prompts: List[str], session_id: str) -> None:
        self._update(task_id, status="running")
        try:
            for prompt in prompts:
                response = self.worker(prompt, session_id=session_id)
                with self._lock:
                    task = self._tasks[task_id]
                    task["results"].append({"prompt": prompt, "response": response})
                    task["completed"] += 1
            self._update(task_id, status="completed")
        except Exception as exc:
            self._update(task_id, status="failed", error=str(exc))

    def _update(self, task_id: str, **changes) -> None:
        with self._lock:
            self._tasks[task_id].update(changes)
