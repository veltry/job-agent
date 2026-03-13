"""
Database - SQLite storage for tracking seen jobs, applications, and history.
"""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)
DB_PATH = Path("storage/jobs.db")


class Database:
    def __init__(self):
        DB_PATH.parent.mkdir(exist_ok=True)
        self.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self._init_schema()
        logger.info(f"📁 Database ready at {DB_PATH}")

    def _init_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS seen_jobs (
                job_id TEXT PRIMARY KEY,
                seen_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                title TEXT,
                company TEXT,
                location TEXT,
                apply_url TEXT,
                score INTEGER,
                status TEXT DEFAULT 'applied',
                applied_at TEXT NOT NULL,
                notes TEXT
            );

            CREATE TABLE IF NOT EXISTS pending_jobs (
                job_id TEXT PRIMARY KEY,
                title TEXT,
                company TEXT,
                location TEXT,
                apply_url TEXT,
                score INTEGER,
                reasons TEXT,
                created_at TEXT NOT NULL
            );
        """)
        self.conn.commit()

    # ── Seen Jobs ─────────────────────────────────────────────

    def is_seen(self, job_id: str) -> bool:
        cur = self.conn.execute("SELECT 1 FROM seen_jobs WHERE job_id = ?", (job_id,))
        return cur.fetchone() is not None

    def mark_seen(self, job_id: str):
        self.conn.execute(
            "INSERT OR IGNORE INTO seen_jobs (job_id, seen_at) VALUES (?, ?)",
            (job_id, datetime.utcnow().isoformat())
        )
        self.conn.commit()

    # ── Pending Jobs (awaiting user confirmation) ─────────────

    def save_pending(self, job: dict, score: int, reasons: list):
        import json
        self.conn.execute("""
            INSERT OR REPLACE INTO pending_jobs
            (job_id, title, company, location, apply_url, score, reasons, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job["id"], job["title"], job["company"], job["location"],
            job["apply_url"], score, json.dumps(reasons),
            datetime.utcnow().isoformat()
        ))
        self.conn.commit()

    def get_pending(self, job_id: str) -> dict | None:
        import json
        cur = self.conn.execute(
            "SELECT * FROM pending_jobs WHERE job_id = ?", (job_id,)
        )
        row = cur.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cur.description]
        data = dict(zip(cols, row))
        data["reasons"] = json.loads(data["reasons"])
        return data

    def delete_pending(self, job_id: str):
        self.conn.execute("DELETE FROM pending_jobs WHERE job_id = ?", (job_id,))
        self.conn.commit()

    # ── Applications ──────────────────────────────────────────

    def save_application(self, job: dict, score: int):
        self.conn.execute("""
            INSERT INTO applications
            (job_id, title, company, location, apply_url, score, status, applied_at)
            VALUES (?, ?, ?, ?, ?, ?, 'applied', ?)
        """, (
            job["job_id"], job["title"], job["company"], job["location"],
            job["apply_url"], score, datetime.utcnow().isoformat()
        ))
        self.conn.commit()

    def get_all_applications(self) -> list:
        cur = self.conn.execute(
            "SELECT title, company, location, score, status, applied_at FROM applications ORDER BY applied_at DESC"
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def get_application_stats(self) -> dict:
        cur = self.conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'applied' THEN 1 ELSE 0 END) as applied,
                AVG(score) as avg_score
            FROM applications
        """)
        row = cur.fetchone()
        return {"total": row[0], "applied": row[1], "avg_score": round(row[2] or 0, 1)}
