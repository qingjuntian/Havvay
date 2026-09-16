import logging
import time
import json

from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from .agent import Agent
from .safety import UnsafePromptError
from .task_queue import TaskQueue, is_long_running_prompt

app = FastAPI(title="Agent Starter")
agent = Agent()
task_queue = TaskQueue(worker=lambda prompt, session_id: agent.run(prompt, session_id=session_id))
logger = logging.getLogger("agent_starter")

class QueryRequest(BaseModel):
    prompt: str
    session_id: str = "default"


class TaskRequest(BaseModel):
    prompts: List[str]
    session_id: str = "default"

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
    try:
        prompt = agent.safety.validate(req.prompt)
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
        resp = agent.run(req.prompt, session_id=req.session_id)
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
            getattr(agent, "last_usage", {}),
        )
    return {
        "response": resp,
        "session_id": req.session_id,
        "usage": getattr(agent, "last_usage", {}),
    }


@app.post("/query/stream")
async def query_stream(req: QueryRequest):
    def event_stream():
        started = time.perf_counter()
        try:
            agent.last_usage = agent._empty_usage()
            yield f"data: {json.dumps({'type': 'status', 'status': 'started'})}\n\n"
            prompt = agent.safety.validate(req.prompt)
            yield f"data: {json.dumps({'type': 'status', 'status': 'retrieving_context'})}\n\n"
            history = agent.memory.get(req.session_id)
            is_follow_up = agent._is_follow_up(prompt, history)
            long_term_ctx = agent.long_term_memory.search(prompt, top_k=2)
            ctx = [] if is_follow_up else agent.retriever.retrieve(prompt, top_k=3)
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
                result = agent.tools.calc(prompt)
                agent.last_usage = agent._empty_usage()
                payload = {
                    "type": "final",
                    "response": result,
                    "session_id": req.session_id,
                    "usage": getattr(agent, "last_usage", {}),
                }
                yield f"data: {json.dumps(payload)}\n\n"
                agent.memory.add(req.session_id, prompt, result)
                agent.long_term_memory.add(req.session_id, prompt, result)
                return

            yield f"data: {json.dumps({'type': 'status', 'status': 'generating'})}\n\n"
            response_chunks = []

            for chunk in agent.iter_model_stream(full):
                response_chunks.append(chunk)
                event = {"type": "chunk", "content": chunk}
                yield f"data: {json.dumps(event)}\n\n"

            response = "".join(response_chunks)
            yield f"data: {json.dumps({'type': 'final', 'content': response, 'session_id': req.session_id, 'usage': agent.last_usage})}\n\n"
            agent.memory.add(req.session_id, prompt, response)
            agent.long_term_memory.add(req.session_id, prompt, response)
        except UnsafePromptError as exc:
            logger.warning("query_rejected session_id=%s reason=%s", req.session_id, str(exc))
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
        except RuntimeError as exc:
            logger.error("query_failed session_id=%s error=%s", req.session_id, str(exc))
            yield f"data: {json.dumps({'type': 'error', 'message': 'Upstream agent service failed.'})}\n\n"
        except Exception as exc:
            logger.exception("query_unexpected_failure session_id=%s", req.session_id)
            yield f"data: {json.dumps({'type': 'error', 'message': 'Internal agent error.'})}\n\n"
        finally:
            logger.info(
                "query_complete session_id=%s duration_ms=%.2f usage=%s",
                req.session_id,
                (time.perf_counter() - started) * 1000,
                getattr(agent, "last_usage", {}),
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
