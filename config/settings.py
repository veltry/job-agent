"""
Settings - All configuration from environment variables.
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # ── Telegram ──────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_USER_ID: int = int(os.getenv("TELEGRAM_USER_ID", "0"))

    # ── Gemini AI ─────────────────────────────────────────────
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = "gemini-2.0-flash-lite"

    # ── Agent Behaviour ───────────────────────────────────────
    MATCH_THRESHOLD: int = int(os.getenv("MATCH_THRESHOLD", "70"))
    SCAN_INTERVAL_HOURS: int = int(os.getenv("SCAN_INTERVAL_HOURS", "4"))
    MAX_JOBS_PER_SCAN: int = int(os.getenv("MAX_JOBS_PER_SCAN", "50"))
    RATE_LIMIT_SECONDS: int = int(os.getenv("RATE_LIMIT_SECONDS", "4"))

    # ── Skills Profile ────────────────────────────────────────
    SKILLS_FILE: Path = Path("config/skills_profile.json")

    @classmethod
    def get_skills_profile(cls) -> dict:
        if cls.SKILLS_FILE.exists():
            with open(cls.SKILLS_FILE) as f:
                return json.load(f)
        raise FileNotFoundError(f"Skills profile not found at {cls.SKILLS_FILE}")

    @classmethod
    def validate(cls):
        errors = []
        if not cls.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN is missing")
        if not cls.TELEGRAM_USER_ID:
            errors.append("TELEGRAM_USER_ID is missing")
        if not cls.GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY is missing")
        if errors:
            raise EnvironmentError("Missing required env vars:\n" + "\n".join(f"  - {e}" for e in errors))
