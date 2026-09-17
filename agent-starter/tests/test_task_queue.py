from queue import Empty
import time

from src.task_queue import TaskQueue


def test_task_queue_replays_and_publishes_lifecycle_events():
    queue = TaskQueue(worker=lambda prompt, session_id: f"done: {prompt}")
    task_id = queue.submit(["first", "second"], session_id="events")
    subscriber = queue.subscribe(task_id)

    events = []
    while True:
        try:
            event = subscriber.get(timeout=2)
        except Empty:
            break
        events.append(event)
        if event["type"] == "status" and event["status"] == "completed":
            break

    assert [event["type"] for event in events] == [
        "status",
        "status",
        "progress",
        "progress",
        "status",
    ]
    assert events[0]["status"] == "queued"
    assert events[1]["status"] == "running"
    assert events[-1]["status"] == "completed"
    assert events[-2]["completed"] == 2
    assert events[-2]["total"] == 2


def test_task_queue_executes_tasks_in_parallel(monkeypatch):
    monkeypatch.setenv("AGENT_TASK_WORKERS", "2")

    def worker(prompt, session_id):
        time.sleep(0.1 if prompt == "first" else 0.01)
        return f"done: {prompt}"

    queue = TaskQueue(worker=worker)
    started = time.perf_counter()
    task_id = queue.submit(["first", "second"])
    subscriber = queue.subscribe(task_id)

    while True:
        event = subscriber.get(timeout=1)
        if event["type"] == "status" and event["status"] == "completed":
            break

    assert time.perf_counter() - started < 0.18
    task = queue.get(task_id)
    assert task["completed"] == 2
    assert task["results"] == [
        {"prompt": "first", "response": "done: first"},
        {"prompt": "second", "response": "done: second"},
    ]
