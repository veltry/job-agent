"""
Settings - Loads all config from environment variables and skills profile.
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # ── Telegram ──────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_USER_ID: int = int(os.getenv("TELEGRAM_USER_ID", "0"))  # Your personal Telegram user ID

    # ── Claude AI ─────────────────────────────────────────────
    CLAUDE_API_KEY: str = os.getenv("CLAUDE_API_KEY", "")
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"

    # ── Apify (LinkedIn Scraper) ───────────────────────────────
    APIFY_API_KEY: str = os.getenv("APIFY_API_KEY", "")
    APIFY_ACTOR_ID: str = "curious_coder/linkedin-jobs-search-scraper"

    # ── Agent Behaviour ───────────────────────────────────────
    MATCH_THRESHOLD: int = 70          # Min score (%) to notify you
    SCAN_INTERVAL_HOURS: int = 4       # How often to scan for new jobs
    MAX_JOBS_PER_SCAN: int = 50        # Max jobs fetched per run

    # ── Skills Profile ────────────────────────────────────────
    SKILLS_FILE: Path = Path("config/skills_profile.json")

    @classmethod
    def get_skills_profile(cls) -> dict:
        if cls.SKILLS_FILE.exists():
            with open(cls.SKILLS_FILE) as f:
                return json.load(f)
        raise FileNotFoundError(f"Skills profile not found at {cls.SKILLS_FILE}. Please create it.")

    @classmethod
    def validate(cls):
        errors = []
        if not cls.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN is missing")
        if not cls.TELEGRAM_USER_ID:
            errors.append("TELEGRAM_USER_ID is missing")
        if not cls.CLAUDE_API_KEY:
            errors.append("CLAUDE_API_KEY is missing")
        if not cls.APIFY_API_KEY:
            errors.append("APIFY_API_KEY is missing")
        if errors:
            raise EnvironmentError("Missing required environment variables:\n" + "\n".join(f"  - {e}" for e in errors))
