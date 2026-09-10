import logging
import time

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .agent import Agent
from .safety import UnsafePromptError

app = FastAPI(title="Agent Starter")
agent = Agent()
logger = logging.getLogger("agent_starter")

class QueryRequest(BaseModel):
    prompt: str
    session_id: str = "default"

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/query")
async def query(req: QueryRequest):
    started = time.perf_counter()
    try:
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
            "query_complete session_id=%s duration_ms=%.2f",
            req.session_id,
            (time.perf_counter() - started) * 1000,
        )
    return {"response": resp, "session_id": req.session_id}
