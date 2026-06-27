"""
main.py
=======
FastAPI application entry point.

Start the server:
    venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
"""
" for running the acuracy test use this command " "venv\Scripts\python.exe -m backend.test_accuracy "

import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.database import init_db, log_scan, get_history, get_stats
from backend.model import firewall_model
from backend.schemas import (
    ScanRequest,
    ScanResponse,
    PaginatedHistory,
    StatsResponse,
    FeatureInfo,
)

# ─── Paths ────────────────────────────────────────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")


# ─── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB and load model on startup."""
    print("[START] AI Firewall starting up...")
    init_db()
    firewall_model.load()
    yield
    print("[STOP] AI Firewall shutting down.")


# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Firewall - LLM Prompt Injection Scanner",
    version="1.0.0",
    description="Real-time NLP-based prompt injection detection API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── API Routes (must be registered BEFORE static mount) ──────────────────────

@app.get("/api/health")
async def health():
    return {
        "status": "online",
        "model_loaded": firewall_model.is_loaded,
        "version": "1.0.0",
    }


@app.post("/api/scan", response_model=ScanResponse)
async def scan_prompt(request: ScanRequest):
    """Analyze a prompt and return a threat verdict."""
    prompt = request.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")
    if len(prompt) > 5000:
        raise HTTPException(status_code=400, detail="Prompt exceeds 5000 character limit.")

    result = firewall_model.predict(prompt)

    scan_id = log_scan(
        prompt_text=prompt,
        verdict=result.verdict,
        confidence=result.confidence,
        category=result.category,
        risk_score=result.risk_score,
        explanation=result.explanation,
        country=request.country or "Unknown",
    )

    return ScanResponse(
        id=scan_id,
        verdict=result.verdict,
        confidence=result.confidence,
        category=result.category,
        risk_score=result.risk_score,
        explanation=result.explanation,
        top_features=[FeatureInfo(**f) for f in result.top_features],
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


@app.get("/api/history", response_model=PaginatedHistory)
async def history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=5, le=100),
    verdict: Optional[str] = Query(default=None),
):
    """Return paginated scan history."""
    data = get_history(page=page, page_size=page_size, verdict_filter=verdict)
    return PaginatedHistory(**data)


@app.get("/api/stats", response_model=StatsResponse)
async def stats():
    """Return aggregate statistics for the dashboard."""
    data = get_stats()
    return StatsResponse(**data)


# ─── Frontend (mounted LAST so /api/* routes take priority) ───────────────────

@app.get("/", include_in_schema=False)
async def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

# Mount static assets (css/, js/) at /static so they don't shadow /api
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
