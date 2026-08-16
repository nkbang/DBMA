"""NAE Live Dashboard — read-only Monitor API.

Only one route reads live state (`GET /api/status`); everything else is
static file serving for the built Vue app. There is deliberately no
POST/PUT/DELETE/PATCH route anywhere in this app — the dashboard cannot
send a command to C1, Ollama, the TSU runner, or Qdrant even if the
frontend tried to, because no such endpoint exists.

Run with:
    uvicorn app:app --host 127.0.0.1 --port 8799
(see ../run_dashboard.sh, which launchd invokes)
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from collector import MonitorState, PollLoop

POLL_INTERVAL_SECONDS = 5.0
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

monitor_state = MonitorState()
poll_loop = PollLoop(monitor_state, interval_seconds=POLL_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    poll_loop.start()
    yield
    poll_loop.stop()


app = FastAPI(title="NAE Live Dashboard Monitor API", lifespan=lifespan)

# Same-origin in normal use (backend serves the built frontend on the same
# port); CORS is only relevant for `npm run dev` against this backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/status")
def get_status() -> JSONResponse:
    return JSONResponse(monitor_state.snapshot())


@app.get("/api/health")
def get_health() -> JSONResponse:
    return JSONResponse({"ok": True})


if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="dashboard")
