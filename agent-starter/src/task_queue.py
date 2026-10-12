"""Small in-process background queue for long-running agent tasks."""

from concurrent.futures import ThreadPoolExecutor
import os
from queue import Queue
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
        max_workers = max(1, int(os.getenv("AGENT_TASK_WORKERS", "4")))
        self.max_retained_tasks = max(1, int(os.getenv("AGENT_TASK_MAX_RETAINED", "1000")))
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="agent-task")
        self._tasks: Dict[str, Dict] = {}
        self._event_history: Dict[str, List[Dict]] = {}
        self._subscribers: Dict[str, List[Queue]] = {}
        self._lock = Lock()

    def submit(self, prompts: List[str], session_id: str = "default") -> str:
        task_id = str(uuid4())
        task = {
            "task_id": task_id,
            "status": "queued",
            "session_id": session_id,
            "total": len(prompts),
            "completed": 0,
            "failed": 0,
            "results": [],
            "_results_by_index": {},
            "error": None,
        }
        with self._lock:
            self._tasks[task_id] = task
            self._event_history[task_id] = []
            self._subscribers[task_id] = []
            self._publish_locked(task_id, {"type": "status", "status": "queued"})
            self._prune_terminal_tasks_locked()
        for prompt_index, prompt in enumerate(prompts):
            self._executor.submit(self._run_prompt, task_id, prompt_index, prompt, session_id)
        return task_id

    def subscribe(self, task_id: str) -> Queue:
        subscriber = Queue()
        with self._lock:
            if task_id not in self._tasks:
                raise KeyError(task_id)
            for event in self._event_history[task_id]:
                subscriber.put(dict(event))
            self._subscribers[task_id].append(subscriber)
        return subscriber

    def unsubscribe(self, task_id: str, subscriber: Queue) -> None:
        with self._lock:
            subscribers = self._subscribers.get(task_id, [])
            if subscriber in subscribers:
                subscribers.remove(subscriber)

    def get(self, task_id: str):
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            task_copy = dict(task)
            results_by_index = task_copy.pop("_results_by_index")
            task_copy["results"] = [results_by_index[index] for index in sorted(results_by_index)]
            return task_copy

    def _run_prompt(self, task_id: str, prompt_index: int, prompt: str, session_id: str) -> None:
        with self._lock:
            task = self._tasks[task_id]
            if task["status"] == "queued":
                task["status"] = "running"
                self._publish_locked(task_id, {"type": "status", "status": "running"})
        try:
            response = self.worker(prompt, session_id=session_id)
        except Exception as exc:
            with self._lock:
                task = self._tasks[task_id]
                task["completed"] += 1
                task["failed"] += 1
                task["_results_by_index"][prompt_index] = {
                    "prompt": prompt,
                    "error": str(exc),
                }
                self._publish_locked(
                    task_id,
                    {
                        "type": "progress",
                        "completed": task["completed"],
                        "total": task["total"],
                        "failed": task["failed"],
                    },
                )
                if task["completed"] == task["total"]:
                    task["status"] = "failed"
                    task["error"] = "One or more prompts failed."
                    self._publish_locked(
                        task_id,
                        {"type": "status", "status": "failed", "error": task["error"]},
                    )
            return

        with self._lock:
            task = self._tasks[task_id]
            task["_results_by_index"][prompt_index] = {"prompt": prompt, "response": response}
            task["completed"] += 1
            self._publish_locked(
                task_id,
                {
                    "type": "progress",
                    "completed": task["completed"],
                    "total": task["total"],
                    "failed": task["failed"],
                },
            )
            if task["completed"] == task["total"]:
                task["status"] = "failed" if task["failed"] else "completed"
                event = {"type": "status", "status": task["status"]}
                if task["failed"]:
                    task["error"] = "One or more prompts failed."
                    event["error"] = task["error"]
                self._publish_locked(task_id, event)
                self._prune_terminal_tasks_locked()

    def _update(self, task_id: str, **changes) -> None:
        with self._lock:
            self._tasks[task_id].update(changes)
            event = {"type": "status", **changes}
            self._publish_locked(task_id, event)

    def _publish_locked(self, task_id: str, event: Dict) -> None:
        event = {"task_id": task_id, **event}
        self._event_history[task_id].append(dict(event))
        for subscriber in self._subscribers.get(task_id, []):
            subscriber.put(dict(event))

    def _prune_terminal_tasks_locked(self) -> None:
        terminal_ids = [
            task_id
            for task_id, task in self._tasks.items()
            if task["status"] in ("completed", "failed")
            and not self._subscribers.get(task_id)
        ]
        excess = len(terminal_ids) - self.max_retained_tasks
        for task_id in terminal_ids[:max(0, excess)]:
            self._tasks.pop(task_id, None)
            self._event_history.pop(task_id, None)
            self._subscribers.pop(task_id, None)
