"""Small in-process background queue for long-running agent tasks."""

from concurrent.futures import ThreadPoolExecutor
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
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="agent-task")
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
            "results": [],
            "error": None,
        }
        with self._lock:
            self._tasks[task_id] = task
            self._event_history[task_id] = []
            self._subscribers[task_id] = []
            self._publish_locked(task_id, {"type": "status", "status": "queued"})
        self._executor.submit(self._run, task_id, list(prompts), session_id)
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
                    self._publish_locked(
                        task_id,
                        {
                            "type": "progress",
                            "completed": task["completed"],
                            "total": task["total"],
                        },
                    )
            self._update(task_id, status="completed")
        except Exception as exc:
            self._update(task_id, status="failed", error=str(exc))

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
