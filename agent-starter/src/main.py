import logging
import time
import json
import uuid
from queue import Empty

from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool
from .agent import Agent
from .graph_workflow import build_graph, default_checkpointer, describe_pending
from .planner import Executor, Planner
from .safety import UnsafePromptError
from .task_queue import TaskQueue, is_long_running_prompt

app = FastAPI(title="Agent Starter")
agent = Agent()
logger = logging.getLogger("agent_starter")


def sse_event(payload):
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def new_request_agent():
    return agent.new_request()


def run_background_task(prompt, session_id):
    result = new_request_agent().plan_and_execute(prompt, session_id=session_id)
    return result.response


task_queue = TaskQueue(worker=run_background_task)

class QueryRequest(BaseModel):
    prompt: str
    session_id: str = "default"


class TaskRequest(BaseModel):
    prompts: List[str]
    session_id: str = "default"


class WorkflowRequest(BaseModel):
    prompt: str
    session_id: str = "default"
    thread_id: Optional[str] = None


class WorkflowResumeRequest(BaseModel):
    approved: bool
    session_id: str = "default"


def _run_workflow(request_agent, thread_id: str, initial_state=None, approved=None):
    graph = build_graph(
        request_agent.run,
        request_agent.tools,
        checkpointer=default_checkpointer(),
        interrupt_before=["human_gate"],
    )
    config = {"configurable": {"thread_id": thread_id}}
    if initial_state is not None:
        graph.invoke(initial_state, config)
    else:
        snapshot = graph.get_state(config)
        if not snapshot.values or not snapshot.next:
            return None
        graph.update_state(
            config,
            {"approved": approved, "log": [f"human {'approved' if approved else 'rejected'}"]},
            as_node="human_gate",
        )
        graph.invoke(None, config)
    return graph.get_state(config)


def _workflow_response(snapshot, request_agent, session_id: str, thread_id: str):
    values = snapshot.values
    if snapshot.next:
        return JSONResponse(
            status_code=202,
            content={
                "thread_id": thread_id,
                "status": "awaiting_approval",
                "pending": describe_pending(values),
                "session_id": session_id,
            },
        )
    return {
        "response": values.get("response", ""),
        "session_id": session_id,
        "thread_id": thread_id,
        "trace": values.get("log", []),
        "usage": getattr(request_agent, "last_usage", {}),
    }

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/tasks", status_code=202)
async def submit_task(req: TaskRequest):
    prompts = [prompt.strip() for prompt in req.prompts if prompt.strip()]
    if not prompts:
        raise HTTPException(status_code=422, detail="At least one non-empty prompt is required.")
    task_id = task_queue.submit(prompts, session_id=req.session_id)
    return {"task_id": task_id, "status": "queued"}


@app.get("/tasks/{task_id}")
async def task_status(task_id: str):
    task = task_queue.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task

@app.post("/query")
async def query(req: QueryRequest):

    started = time.perf_counter()
    request_agent = new_request_agent()
    try:
        prompt = request_agent.safety.validate(req.prompt)
        if is_long_running_prompt(prompt):
            task_id = task_queue.submit([prompt], session_id=req.session_id)
            return JSONResponse(
                status_code=202,
                content={
                    "task_id": task_id,
                    "status": "queued",
                    "execution_mode": "background",
                    "session_id": req.session_id,
                },
            )
        if hasattr(request_agent, "plan_and_execute"):
            planned = await run_in_threadpool(
                request_agent.plan_and_execute, req.prompt, req.session_id
            )
            resp = planned.response
        else:
            resp = await run_in_threadpool(request_agent.run, req.prompt, req.session_id)
    except UnsafePromptError as exc:
        logger.warning("query_rejected session_id=%s reason=%s", req.session_id, str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.error("query_failed session_id=%s error=%s", req.session_id, str(exc))
        raise HTTPException(status_code=502, detail="Upstream agent service failed.") from exc
    except Exception as exc:
        logger.exception("query_unexpected_failure session_id=%s", req.session_id)
        raise HTTPException(status_code=500, detail="Internal agent error.") from exc
    finally:
        logger.info(
            "query_complete session_id=%s duration_ms=%.2f usage=%s",
            req.session_id,
            (time.perf_counter() - started) * 1000,
            getattr(request_agent, "last_usage", {}),
        )
    return {
        "response": resp,
        "session_id": req.session_id,
        "usage": getattr(request_agent, "last_usage", {}),
    }


@app.post("/query/multi-agent")
async def query_multi_agent(req: QueryRequest):
    started = time.perf_counter()
    request_agent = new_request_agent()
    try:
        prompt = request_agent.safety.validate(req.prompt)
        result = await run_in_threadpool(
            request_agent.multi_agent_plan_and_execute, prompt, req.session_id
        )
    except UnsafePromptError as exc:
        logger.warning("multi_agent_query_rejected session_id=%s reason=%s", req.session_id, str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.error("multi_agent_query_failed session_id=%s error=%s", req.session_id, str(exc))
        raise HTTPException(status_code=502, detail="Upstream agent service failed.") from exc
    except Exception as exc:
        logger.exception("multi_agent_query_unexpected_failure session_id=%s", req.session_id)
        raise HTTPException(status_code=500, detail="Internal agent error.") from exc
    finally:
        logger.info(
            "multi_agent_query_complete session_id=%s duration_ms=%.2f usage=%s",
            req.session_id,
            (time.perf_counter() - started) * 1000,
            getattr(request_agent, "last_usage", {}),
        )
    return {
        "response": result.response,
        "session_id": req.session_id,
        "usage": getattr(request_agent, "last_usage", {}),
    }


@app.post("/query/workflow")
async def query_workflow(req: WorkflowRequest):
    """LangGraph workflow: branching, model retry, and human tool approval.

    Returns 200 with the final response, or 202 when the run is paused at the
    human approval gate; resume with POST /query/workflow/{thread_id}/resume.
    """
    request_agent = new_request_agent()
    try:
        prompt = request_agent.safety.validate(req.prompt)
        thread_id = req.thread_id or uuid.uuid4().hex
        initial_state = {
            "prompt": prompt,
            "session_id": req.session_id,
            "approved": None,
            "attempts": 0,
            "log": [],
        }
        snapshot = await run_in_threadpool(
            _run_workflow, request_agent, thread_id, initial_state
        )
    except UnsafePromptError as exc:
        logger.warning("workflow_query_rejected session_id=%s reason=%s", req.session_id, str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.error("workflow_query_failed session_id=%s error=%s", req.session_id, str(exc))
        raise HTTPException(status_code=502, detail="Upstream agent service failed.") from exc
    except Exception as exc:
        logger.exception("workflow_query_unexpected_failure session_id=%s", req.session_id)
        raise HTTPException(status_code=500, detail="Internal agent error.") from exc
    return _workflow_response(snapshot, request_agent, req.session_id, thread_id)


@app.post("/query/workflow/{thread_id}/resume")
async def resume_workflow(thread_id: str, req: WorkflowResumeRequest):
    """Approve or reject a paused workflow run and resume it."""
    request_agent = new_request_agent()
    try:
        snapshot = await run_in_threadpool(
            _run_workflow, request_agent, thread_id, None, req.approved
        )
    except Exception as exc:
        logger.exception("workflow_resume_unexpected_failure thread_id=%s", thread_id)
        raise HTTPException(status_code=500, detail="Internal agent error.") from exc
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Workflow run not found or already finished.")
    return _workflow_response(snapshot, request_agent, req.session_id, thread_id)


@app.post("/query/stream")
async def query_stream(req: QueryRequest):
    def event_stream():
        started = time.perf_counter()
        request_agent = new_request_agent()
        try:
            request_agent.last_usage = request_agent._empty_usage()
            yield sse_event({"type": "status", "status": "started"})
            prompt = request_agent.safety.validate(req.prompt)
            if is_long_running_prompt(prompt):
                task_id = task_queue.submit([prompt], session_id=req.session_id)
                subscriber = task_queue.subscribe(task_id)
                try:
                    while True:
                        try:
                            event = subscriber.get(timeout=15)
                        except Empty:
                            yield sse_event({"type": "heartbeat", "task_id": task_id})
                            continue

                        yield sse_event(event)
                        if event.get("type") != "status":
                            continue
                        if event.get("status") == "completed":
                            task = task_queue.get(task_id)
                            result = task["results"][-1]["response"] if task and task["results"] else ""
                            yield sse_event({"type": "final", "task_id": task_id, "content": result, "session_id": req.session_id})
                            return
                        if event.get("status") == "failed":
                            yield sse_event({"type": "error", "task_id": task_id, "message": event.get("error", "Task failed")})
                            return
                finally:
                    task_queue.unsubscribe(task_id, subscriber)

            plan = Planner(safety=request_agent.safety).plan(prompt)
            if len(plan) > 1 or plan[0].action == "tool":
                yield sse_event({"type": "status", "status": "executing_plan"})
                result = Executor(request_agent).execute(plan, session_id=req.session_id)
                for step, output in zip(result.steps, result.outputs):
                    yield sse_event({
                        "type": "step",
                        "step_id": step.id,
                        "action": step.action,
                        "tool": step.tool,
                        "content": output,
                    })
                yield sse_event({
                    "type": "final",
                    "content": result.response,
                    "session_id": req.session_id,
                    "usage": getattr(request_agent, "last_usage", {}),
                })
                return

            yield sse_event({"type": "status", "status": "retrieving_context"})
            history = request_agent.memory.get(req.session_id)
            is_follow_up = request_agent._is_follow_up(prompt, history)
            long_term_ctx = request_agent.long_term_memory.search(prompt, top_k=2)
            ctx = [] if is_follow_up else request_agent.retriever.retrieve(prompt, top_k=3)
            memory_block = "\n---\n".join(long_term_ctx) if long_term_ctx else "No relevant long-term memory found."
            full = """
Long-term memory (use only when relevant):
{}

Document context (use only when relevant):
{}

Current user message:
{}
""".format(memory_block, "\n---\n".join(ctx), prompt)
            if history:
                full = """Conversation history (primary context for this follow-up):
{}

{}

Answer the current message as a continuation of the conversation. Do not replace
the conversation topic with document context unless the user explicitly asks about
the documents.
""".format(
                    "\n".join(f"{turn['role']}: {turn['content']}" for turn in history),
                    full,
                )

            if "calculate" in prompt.lower():
                result = request_agent.tools.calc(prompt)
                request_agent.last_usage = request_agent._empty_usage()
                payload = {
                    "type": "final",
                    "content": result,
                    "session_id": req.session_id,
                    "usage": getattr(request_agent, "last_usage", {}),
                }
                yield sse_event(payload)
                request_agent.memory.add(req.session_id, prompt, result)
                request_agent.long_term_memory.add(req.session_id, prompt, result)
                return

            yield sse_event({"type": "status", "status": "generating"})
            response_chunks = []

            for chunk in request_agent.iter_model_stream(full):
                response_chunks.append(chunk)
                event = {"type": "chunk", "content": chunk}
                yield sse_event(event)

            response = "".join(response_chunks)
            yield sse_event({"type": "final", "content": response, "session_id": req.session_id, "usage": request_agent.last_usage})
            request_agent.memory.add(req.session_id, prompt, response)
            request_agent.long_term_memory.add(req.session_id, prompt, response)
        except UnsafePromptError as exc:
            logger.warning("query_rejected session_id=%s reason=%s", req.session_id, str(exc))
            yield sse_event({"type": "error", "message": str(exc)})
        except RuntimeError as exc:
            logger.error("query_failed session_id=%s error=%s", req.session_id, str(exc))
            yield sse_event({"type": "error", "message": "Upstream agent service failed."})
        except Exception as exc:
            logger.exception("query_unexpected_failure session_id=%s", req.session_id)
            yield sse_event({"type": "error", "message": "Internal agent error."})
        finally:
            logger.info(
                "query_complete session_id=%s duration_ms=%.2f usage=%s",
                req.session_id,
                (time.perf_counter() - started) * 1000,
                getattr(request_agent, "last_usage", {}),
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
