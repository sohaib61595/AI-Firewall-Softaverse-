import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "firewall.db")

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
    """Initialize the database schema."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
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

    # Simple migration: try to add the column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE scan_logs ADD COLUMN country TEXT DEFAULT 'Unknown'")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


def log_scan(
    prompt_text: str,
    verdict: str,
    confidence: float,
    category: str,
    risk_score: int,
    explanation: str,
    country: str = "Unknown",
) -> int:
    """Insert a new scan record and return the auto-incremented ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO scan_logs (prompt_text, verdict, confidence, category, risk_score, explanation, timestamp, country)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            prompt_text,
            verdict,
            confidence,
            category,
            risk_score,
            explanation,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            country,
        ),
    )
    conn.commit()
    row_id = cursor.lastrowid or 0
    conn.close()
    return row_id


def get_history(page: int = 1, page_size: int = 20, verdict_filter: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve paginated scan history."""
    conn = get_connection()
    cursor = conn.cursor()

    base_where = ""
    params_count: List[Any] = []
    params_data: List[Any] = []

    if verdict_filter and verdict_filter.upper() in ("SAFE", "BLOCKED"):
        base_where = "WHERE verdict = ?"
        params_count.append(verdict_filter.upper())
        params_data.append(verdict_filter.upper())

    # Total count
    cursor.execute(f"SELECT COUNT(*) FROM scan_logs {base_where}", params_count)
    total = cursor.fetchone()[0]

    offset = (page - 1) * page_size
    params_data.extend([page_size, offset])

    cursor.execute(
        f"""
        SELECT id, prompt_text, verdict, confidence, category, risk_score, timestamp
        FROM scan_logs {base_where}
        ORDER BY id DESC
        LIMIT ? OFFSET ?
        """,
        params_data,
    )
    rows = cursor.fetchall()
    conn.close()

    items = []
    for row in rows:
        items.append(
            {
                "id": row["id"],
                "prompt_preview": row["prompt_text"][:120] + ("..." if len(row["prompt_text"]) > 120 else ""),
                "verdict": row["verdict"],
                "confidence": row["confidence"],
                "category": row["category"],
                "risk_score": row["risk_score"],
                "timestamp": row["timestamp"],
            }
        )

    import math
    total_pages = max(1, math.ceil(total / page_size))

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def get_stats() -> Dict[str, Any]:
    """Aggregate statistics for the dashboard."""
    conn = get_connection()
    cursor = conn.cursor()

    # Overall counts
    cursor.execute("SELECT COUNT(*) FROM scan_logs")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM scan_logs WHERE verdict = 'BLOCKED'")
    blocked = cursor.fetchone()[0]

    safe = total - blocked
    block_rate = round((blocked / total * 100) if total > 0 else 0.0, 1)

    # Categories
    cursor.execute(
        "SELECT category, COUNT(*) as cnt FROM scan_logs GROUP BY category ORDER BY cnt DESC"
    )
    cat_rows = cursor.fetchall()
    categories = [
        {
            "category": r["category"],
            "count": r["cnt"],
            "color": CATEGORY_COLORS.get(r["category"], "#888888"),
        }
        for r in cat_rows
    ]

    # Hourly trend (last 24 hours)
    hourly = []
    now = datetime.now()
    for h in range(23, -1, -1):
        hour_start = (now - timedelta(hours=h)).strftime("%Y-%m-%d %H:00:00")
        hour_end = (now - timedelta(hours=h - 1)).strftime("%Y-%m-%d %H:00:00") if h > 0 else now.strftime("%Y-%m-%d %H:%M:%S")
        hour_label = (now - timedelta(hours=h)).strftime("%H:00")

        cursor.execute(
            "SELECT COUNT(*) FROM scan_logs WHERE timestamp >= ? AND timestamp < ? AND verdict = 'SAFE'",
            (hour_start, hour_end),
        )
        safe_h = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM scan_logs WHERE timestamp >= ? AND timestamp < ? AND verdict = 'BLOCKED'",
            (hour_start, hour_end),
        )
        blocked_h = cursor.fetchone()[0]

        hourly.append({"hour": hour_label, "safe": safe_h, "blocked": blocked_h})

    # Recent threats
    cursor.execute(
        """
        SELECT id, prompt_text, verdict, confidence, category, risk_score, timestamp
        FROM scan_logs WHERE verdict = 'BLOCKED'
        ORDER BY id DESC LIMIT 5
        """
    )
    threat_rows = cursor.fetchall()
    conn.close()

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
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT country, COUNT(*) as cnt FROM scan_logs WHERE verdict = 'BLOCKED' GROUP BY country"
    )
    country_rows = cursor.fetchall()
    country_blocks = {r["country"]: r["cnt"] for r in country_rows}
    
    # Top 5 countries
    top_countries = sorted([{"country": k, "count": v} for k, v in country_blocks.items() if k != "Unknown"], key=lambda x: x["count"], reverse=True)[:5]
    conn.close()

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
    """Delete all entries from the scan_logs table."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM scan_logs")
    conn.commit()
    conn.close()

