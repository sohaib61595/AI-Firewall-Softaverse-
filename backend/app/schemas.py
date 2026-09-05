"""
backend/app/schemas.py
======================
Pydantic Request/Response models for API endpoints.
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ScanRequest(BaseModel):
    prompt: str
    country: Optional[str] = "Unknown"


class FeatureInfo(BaseModel):
    feature: str
    weight: float


class ScanResponse(BaseModel):
    id: int
    verdict: str  # "SAFE" or "BLOCKED"
    confidence: float
    category: str
    risk_score: int  # 0-100
    explanation: str
    top_features: List[FeatureInfo]
    timestamp: str


class HistoryItem(BaseModel):
    id: int
    prompt_preview: str
    verdict: str
    confidence: float
    category: str
    risk_score: int
    timestamp: str


class PaginatedHistory(BaseModel):
    items: List[HistoryItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class CategoryStat(BaseModel):
    category: str
    count: int
    color: str


class HourlyPoint(BaseModel):
    hour: str
    safe: int
    blocked: int


class TopCountry(BaseModel):
    country: str
    count: int


class StatsResponse(BaseModel):
    total_scans: int
    blocked_count: int
    safe_count: int
    block_rate: float
    categories: List[CategoryStat]
    hourly_trend: List[HourlyPoint]
    recent_threats: List[HistoryItem]
    country_blocks: dict
    top_countries: List[TopCountry]


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    reply: str
    status: str
    firewall_label: Optional[str] = None
