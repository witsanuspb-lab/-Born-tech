"""FastAPI web server — run with: uvicorn app:app --reload --port 8000"""
import asyncio
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from config import Config
from memory.store import MemoryStore
from team import build_team
from utils.cost import get_tracker, reset_tracker

_executor = ThreadPoolExecutor(max_workers=4)
_team = None
_memory = None
_history: list[dict] = []  # [{task, result, trace, cost}]


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _team, _memory
    cfg = Config(verbose=False)
    _memory = MemoryStore()
    _team = build_team(cfg, memory=_memory)
    yield
    _executor.shutdown(wait=False)


app = FastAPI(title="AI Team", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── Models ──────────────────────────────────────────────────────────────────

class TaskRequest(BaseModel):
    task: str
    chat_mode: bool = False

class MemoryRequest(BaseModel):
    key: str
    value: str

class ConfigRequest(BaseModel):
    chat_mode: bool | None = None
    verbose: bool | None = None


# ── Routes ──────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    html_path = Path("static/index.html")
    if not html_path.exists():
        return HTMLResponse("<h1>static/index.html not found</h1>", status_code=404)
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.post("/api/run")
async def run_task(req: TaskRequest):
    if _team is None:
        raise HTTPException(status_code=503, detail="Team not ready")

    _team.maintain_history = req.chat_mode
    reset_tracker()

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(_executor, _team.run, req.task)

    entry = {
        "task": req.task,
        "result": result,
        "trace": _team.last_trace,
        "cost": get_tracker().summary(),
    }
    _history.append(entry)

    return entry


@app.get("/api/history")
async def get_history():
    return {"history": _history}


@app.delete("/api/history")
async def clear_history():
    _history.clear()
    _team.clear_history()
    reset_tracker()
    return {"message": "History cleared"}


@app.get("/api/memories")
async def get_memories():
    return {"memories": _memory.as_dict() if _memory else {}}


@app.post("/api/memories")
async def save_memory(req: MemoryRequest):
    if not _memory:
        raise HTTPException(status_code=503, detail="Memory not ready")
    result = _memory.save(req.key, req.value)
    return {"message": result}


@app.delete("/api/memories/{key}")
async def delete_memory(key: str):
    if not _memory:
        raise HTTPException(status_code=503, detail="Memory not ready")
    result = _memory.delete(key)
    return {"message": result}


@app.get("/api/cost")
async def get_cost():
    return {"summary": get_tracker().summary()}


@app.get("/api/health")
async def health():
    return {"status": "ok", "agents": list(_team.agents.keys()) if _team else []}
