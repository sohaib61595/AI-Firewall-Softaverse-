"""
backend/app/database.py
=======================
SQLite database manager for scan logs and dashboard analytics.
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "firewall.db")

CATEGORY_COLORS = {
    "SAFE": "#00ff88",
    "JAILBREAK": "#ff3366",
    "ROLE_PLAY_BYPASS": "#ff9500",
    "PAYLOAD_INJECTION": "#cc00ff",
    "SOCIAL_ENGINEERING": "#ff6b35",
    "DATA_EXFILTRATION": "#4d9fff",
}


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the scan_logs table if it does not exist."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scan_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_text TEXT    NOT NULL,
                verdict     TEXT    NOT NULL,
                confidence  REAL    NOT NULL,
                category    TEXT    NOT NULL,
                risk_score  INTEGER NOT NULL,
                explanation TEXT,
                timestamp   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
                country     TEXT    DEFAULT 'Unknown'
            )
        """)


def log_scan(prompt_text: str, verdict: str, confidence: float, category: str,
             risk_score: int, explanation: str, country: str = "Unknown") -> int:
    """Insert a new scan record and return its row ID."""
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO scan_logs (prompt_text, verdict, confidence, category, risk_score, explanation, timestamp, country)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (prompt_text, verdict, confidence, category, risk_score, explanation,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"), country),
        )
        return cur.lastrowid or 0


def get_history(page: int = 1, page_size: int = 20, verdict_filter: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve paginated audit history."""
    with get_connection() as conn:
        where = "WHERE verdict = ?" if verdict_filter and verdict_filter.upper() in ("SAFE", "BLOCKED") else ""
        params = [verdict_filter.upper()] if where else []

        total = conn.execute(f"SELECT COUNT(*) FROM scan_logs {where}", params).fetchone()[0]

        rows = conn.execute(
            f"""
            SELECT id, prompt_text, verdict, confidence, category, risk_score, timestamp
            FROM scan_logs {where}
            ORDER BY id DESC LIMIT ? OFFSET ?
            """,
            params + [page_size, (page - 1) * page_size],
        ).fetchall()

    items = [
        {
            "id": r["id"],
            "prompt_preview": r["prompt_text"][:120] + ("..." if len(r["prompt_text"]) > 120 else ""),
            "verdict": r["verdict"],
            "confidence": r["confidence"],
            "category": r["category"],
            "risk_score": r["risk_score"],
            "timestamp": r["timestamp"],
        }
        for r in rows
    ]
    total_pages = max(1, (total + page_size - 1) // page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size, "total_pages": total_pages}


def get_stats() -> Dict[str, Any]:
    """Aggregate metrics for the operations dashboard."""
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM scan_logs").fetchone()[0]
        blocked = conn.execute("SELECT COUNT(*) FROM scan_logs WHERE verdict = 'BLOCKED'").fetchone()[0]
        safe = total - blocked
        block_rate = round((blocked / total * 100) if total > 0 else 0.0, 1)

        # Categories
        cat_rows = conn.execute("SELECT category, COUNT(*) as cnt FROM scan_logs GROUP BY category ORDER BY cnt DESC").fetchall()
        categories = [{"category": r["category"], "count": r["cnt"], "color": CATEGORY_COLORS.get(r["category"], "#888888")} for r in cat_rows]

        # 24-Hour Trend (single query)
        now = datetime.now()
        hourly_map = {(now - timedelta(hours=h)).strftime("%H:00"): {"safe": 0, "blocked": 0} for h in range(23, -1, -1)}
        cutoff = (now - timedelta(hours=24)).strftime("%Y-%m-%d %H:00:00")
        trend_rows = conn.execute(
            "SELECT strftime('%H:00', timestamp) as hr, verdict, COUNT(*) as cnt FROM scan_logs WHERE timestamp >= ? GROUP BY hr, verdict",
            (cutoff,),
        ).fetchall()
        for r in trend_rows:
            if r["hr"] in hourly_map:
                key = "safe" if r["verdict"] == "SAFE" else "blocked"
                hourly_map[r["hr"]][key] += r["cnt"]

        hourly = [{"hour": hr, "safe": d["safe"], "blocked": d["blocked"]} for hr, d in hourly_map.items()]

        # Recent 5 threats
        threat_rows = conn.execute(
            "SELECT id, prompt_text, verdict, confidence, category, risk_score, timestamp FROM scan_logs WHERE verdict = 'BLOCKED' ORDER BY id DESC LIMIT 5"
        ).fetchall()
        recent_threats = [
            {
                "id": r["id"],
                "prompt_preview": r["prompt_text"][:80] + ("..." if len(r["prompt_text"]) > 80 else ""),
                "verdict": r["verdict"],
                "confidence": r["confidence"],
                "category": r["category"],
                "risk_score": r["risk_score"],
                "timestamp": r["timestamp"],
            }
            for r in threat_rows
        ]

        # Country blocks
        c_rows = conn.execute("SELECT country, COUNT(*) as cnt FROM scan_logs WHERE verdict = 'BLOCKED' GROUP BY country").fetchall()
        country_blocks = {r["country"]: r["cnt"] for r in c_rows}
        top_countries = sorted([{"country": k, "count": v} for k, v in country_blocks.items() if k != "Unknown"], key=lambda x: x["count"], reverse=True)[:5]

    return {
        "total_scans": total,
        "blocked_count": blocked,
        "safe_count": safe,
        "block_rate": block_rate,
        "categories": categories,
        "hourly_trend": hourly,
        "recent_threats": recent_threats,
        "country_blocks": country_blocks,
        "top_countries": top_countries,
    }


def clear_history():
    """Delete all records from scan_logs."""
    with get_connection() as conn:
        conn.execute("DELETE FROM scan_logs")
