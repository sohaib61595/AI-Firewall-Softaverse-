"""
main.py
=======
FastAPI application entry point.

Start the server:
    venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
"""
" for running the acuracy test use this command " "venv\Scripts\python.exe -m backend.test_accuracy "

import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI
from cachetools import TTLCache

# Load environment variables from backend/.env
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path)

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
    ChatRequest,
    ChatResponse,
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

# ─── Chatbot State ────────────────────────────────────────────────────────────
# SESSIONS stores conversation history: bounded by maxsize and ttl
SESSIONS = TTLCache(maxsize=1000, ttl=3600)

# RATE_LIMIT_STORE tracks blocks and normal requests
RATE_LIMIT_STORE = TTLCache(maxsize=10000, ttl=60)
RATE_LIMIT_MAX_BLOCKS = 3
RATE_LIMIT_MAX_REQS = 10

def check_rate_limits(session_id: str, is_block: bool = False) -> tuple[bool, str]:
    if session_id not in RATE_LIMIT_STORE:
        RATE_LIMIT_STORE[session_id] = {"blocks": 0, "reqs": 0}
    
    stats = RATE_LIMIT_STORE[session_id]
    if is_block:
        stats["blocks"] += 1
    else:
        stats["reqs"] += 1
        
    if stats["blocks"] >= RATE_LIMIT_MAX_BLOCKS:
        return True, "blocked"
    if stats["reqs"] > RATE_LIMIT_MAX_REQS:
        return True, "rate_limited"
        
    return False, ""



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


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Main chatbot endpoint.
    1. Check rate limits.
    2. Pass through AI Firewall.
    3. If SAFE, append to history and query LLM (Anthropic or fallback).
    4. If JAILBREAK, block and log.
    """
    session_id = request.session_id
    user_msg = request.message.strip()
    
    if not user_msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # 1. Rate Limiting Check (Global)
    is_limited, limit_reason = check_rate_limits(session_id, is_block=False)
    if is_limited:
        if limit_reason == "blocked":
            msg = "You have been temporarily blocked due to repeated security violations. Please try again later."
        else:
            msg = "Rate limit exceeded. Please wait a minute before sending more messages."
            
        return ChatResponse(
            reply=msg,
            status="rate_limited",
            firewall_label="BLOCKED (RATE LIMIT)"
        )

    # 2. Firewall Check
    result = firewall_model.predict(user_msg)
    
    if result.verdict == "JAILBREAK" or result.verdict == "BLOCKED":
        # Log the blocked attempt
        log_scan(
            prompt_text=user_msg,
            verdict="BLOCKED",
            confidence=result.confidence,
            category=result.category,
            risk_score=result.risk_score,
            explanation=result.explanation,
            country="Unknown" # For chat we assume unknown or extract from headers later
        )
        
        # Record attempt for rate limiting
        check_rate_limits(session_id, is_block=True)
        
        return ChatResponse(
            reply="This message was flagged by our security filter and cannot be processed.",
            status="blocked",
            firewall_label=f"BLOCKED ({result.category})"
        )
        
    # 3. If SAFE, query LLM
    # Log the safe prompt too for visibility in dashboard
    log_scan(
        prompt_text=user_msg,
        verdict="SAFE",
        confidence=result.confidence,
        category=result.category,
        risk_score=result.risk_score,
        explanation=result.explanation,
        country="Unknown"
    )

    if session_id not in SESSIONS:
        SESSIONS[session_id] = []
        
    history = SESSIONS[session_id]
    history.append({"role": "user", "content": user_msg})
    
    model_name = os.environ.get("LLM_MODEL", "").replace("openrouter/", "")
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not model_name or not api_key:
        # Fallback Mock Responder
        bot_reply = f"[MOCK RESPONDER - API Key/Model missing] I received your message: '{user_msg}'. You are marked as SAFE."
    else:
        try:
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
            )
            response = client.chat.completions.create(
                model=model_name,
                messages=history
            )
            bot_reply = response.choices[0].message.content
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "rate limit" in error_msg.lower():
                bot_reply = "Rate limit exceeded. Please try again in a few moments."
            else:
                bot_reply = f"[ERROR] Failed to communicate with LLM: {error_msg}"
            
    history.append({"role": "assistant", "content": bot_reply})
    
    # Cap history length to prevent context explosion
    if len(history) > 20:
        SESSIONS[session_id] = history[-20:]

    return ChatResponse(
        reply=bot_reply,
        status="success",
        firewall_label="SAFE"
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


@app.delete("/api/history")
async def clear_history_api():
    from backend.database import clear_history
    try:
        clear_history()
        return {"status": "success", "message": "History cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
