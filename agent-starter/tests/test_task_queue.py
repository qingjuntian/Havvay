from queue import Empty

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
