from fastapi import FastAPI
from pydantic import BaseModel
from .agent import Agent

app = FastAPI(title="Agent Starter")
agent = Agent()

class QueryRequest(BaseModel):
    prompt: str

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/query")
async def query(req: QueryRequest):
    resp = agent.run(req.prompt)
    return {"response": resp}
