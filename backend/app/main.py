"""
backend/app/main.py
===================
FastAPI application service for the AI Firewall.
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI
from cachetools import TTLCache
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.database import init_db, log_scan, get_history, get_stats, clear_history
from backend.core.model import firewall_model
from backend.app.schemas import (
    ScanRequest, ScanResponse, PaginatedHistory,
    StatsResponse, FeatureInfo, ChatRequest, ChatResponse
)

# Load environment configuration from backend/.env
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(env_path)

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB and load ML model on startup."""
    init_db()
    firewall_model.load()
    yield


# Reload trigger: 2023-10-27 10:00:00
app = FastAPI(title="AI Firewall", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Chatbot state & Rate limiting
SESSIONS = TTLCache(maxsize=1000, ttl=3600)
RATE_LIMIT_STORE = TTLCache(maxsize=10000, ttl=60)


def check_rate_limits(session_id: str, is_block: bool = False) -> tuple[bool, str]:
    """Check if session exceeded rate limit (10 reqs/min) or block threshold (3 violations/min)."""
    if session_id not in RATE_LIMIT_STORE:
        RATE_LIMIT_STORE[session_id] = {"blocks": 0, "reqs": 0}
    stats = RATE_LIMIT_STORE[session_id]
    if is_block:
        stats["blocks"] += 1
    else:
        stats["reqs"] += 1

    if stats["blocks"] >= 3:
        return True, "blocked"
    if stats["reqs"] > 10:
        return True, "rate_limited"
    return False, ""


def call_llm(messages: list) -> str:
    """Query OpenRouter LLM or provide fallback response."""
    model = os.environ.get("LLM_MODEL", "").replace("openrouter/", "")
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not model or not api_key:
        last_msg = messages[-1]["content"] if messages else ""
        return f"[AI Assistant] Received your query: '{last_msg}'. Protected by AI Firewall."
    try:
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
        resp = client.chat.completions.create(model=model, messages=messages)
        return resp.choices[0].message.content
    except Exception as e:
        err = str(e)
        if "429" in err or "rate limit" in err.lower():
            return "Rate limit reached on AI Provider. Please try again shortly."
        return f"AI response unavailable: {err}"


# ─── API Endpoints ────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "online", "model_loaded": firewall_model.is_loaded, "version": "1.0.0"}


@app.post("/api/scan", response_model=ScanResponse)
async def scan_prompt(request: ScanRequest):
    """Analyze input prompt and return detailed risk analytics."""
    prompt = request.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")
    if len(prompt) > 50000:
        raise HTTPException(status_code=400, detail="Prompt exceeds 50,000 character limit.")

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


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Protected chatbot endpoint enforcing 1,000-character limit and real-time firewall."""
    session_id = request.session_id
    user_msg = request.message.strip()

    if not user_msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    if len(user_msg) > 1000:
        raise HTTPException(status_code=400, detail="Message exceeds 1,000 character limit.")

    # 1. Rate Limiting Check
    limited, reason = check_rate_limits(session_id, is_block=False)
    if limited:
        msg = "Temporarily blocked due to repeated violations." if reason == "blocked" else "Rate limit exceeded. Please wait a minute."
        return ChatResponse(reply=msg, status="rate_limited", firewall_label="BLOCKED (RATE LIMIT)")

    # 2. Firewall Analysis
    result = firewall_model.predict(user_msg)

    # 3. If Attack Detected -> Intercept and log
    if result.verdict in ("JAILBREAK", "BLOCKED"):
        log_scan(user_msg, "BLOCKED", result.confidence, result.category, result.risk_score, result.explanation)
        check_rate_limits(session_id, is_block=True)
        return ChatResponse(
            reply="This message was flagged by our security firewall and cannot be processed.",
            status="blocked",
            firewall_label=f"BLOCKED ({result.category})",
        )

    # 4. If Safe -> Log, record history, and query LLM
    log_scan(user_msg, "SAFE", result.confidence, result.category, result.risk_score, result.explanation)
    if session_id not in SESSIONS:
        SESSIONS[session_id] = []
    history = SESSIONS[session_id]
    history.append({"role": "user", "content": user_msg})

    bot_reply = call_llm(history)
    history.append({"role": "assistant", "content": bot_reply})
    if len(history) > 20:
        SESSIONS[session_id] = history[-20:]

    return ChatResponse(reply=bot_reply, status="success", firewall_label="SAFE")


@app.get("/api/history", response_model=PaginatedHistory)
async def history(page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=5, le=100), verdict: Optional[str] = None):
    return PaginatedHistory(**get_history(page=page, page_size=page_size, verdict_filter=verdict))


@app.delete("/api/history")
async def clear_history_api():
    try:
        clear_history()
        return {"status": "success", "message": "History cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats", response_model=StatsResponse)
async def stats():
    return StatsResponse(**get_stats())


# ─── Static HTML UI Routes ───────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
@app.get("/admin", include_in_schema=False)
async def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/chat", include_in_schema=False)
async def serve_chat():
    return FileResponse(os.path.join(FRONTEND_DIR, "chat.html"))


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
