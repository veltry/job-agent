"""
Tests - Run before deployment to catch issues early.
"""

import pytest
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Settings Tests ────────────────────────────────────────────

def test_skills_profile_exists():
    """Skills profile file must exist."""
    from config.settings import Settings
    assert Settings.SKILLS_FILE.exists(), "skills_profile.json not found!"


def test_skills_profile_valid():
    """Skills profile must have required fields."""
    from config.settings import Settings
    profile = Settings.get_skills_profile()
    required = ["name", "title", "skills", "preferred_roles",
                "preferred_locations", "job_search_keywords"]
    for field in required:
        assert field in profile, f"Missing field in skills_profile.json: {field}"


def test_skills_not_empty():
    """Skills list must not be empty."""
    from config.settings import Settings
    profile = Settings.get_skills_profile()
    assert len(profile.get("skills", [])) > 0, "Skills list is empty!"
    assert len(profile.get("job_search_keywords", [])) > 0, "Keywords list is empty!"


# ── Database Tests ────────────────────────────────────────────

def test_database_creates():
    """Database should initialize without errors."""
    import tempfile
    from pathlib import Path
    from unittest.mock import patch

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        with patch("storage.database.DB_PATH", db_path):
            from storage.database import Database
            db = Database()
            assert db_path.exists()


def test_database_seen_jobs():
    """Seen jobs tracking should work correctly."""
    import tempfile
    from pathlib import Path
    from unittest.mock import patch

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        with patch("storage.database.DB_PATH", db_path):
            from storage.database import Database
            db = Database()

            assert not db.is_seen("job_123")
            db.mark_seen("job_123")
            assert db.is_seen("job_123")
            assert not db.is_seen("job_456")


# ── Scraper Tests ─────────────────────────────────────────────

def test_scraper_initializes():
    """Scraper should initialize with skills profile."""
    from scrapers.job_scraper import JobScraper
    scraper = JobScraper()
    assert scraper.profile is not None


def test_job_normalization():
    """Jobs should have required fields after normalization."""
    required_fields = ["id", "title", "company", "location",
                      "description", "apply_url", "employment_type"]

    sample_job = {
        "id": "test_123",
        "title": "Java Developer",
        "company": "Test Corp",
        "location": "Remote",
        "description": "Looking for Java developer...",
        "apply_url": "https://example.com/job",
        "employment_type": "Full-time",
        "source": "Jobicy",
        "salary": "Not disclosed",
        "posted_at": "2026-01-01"
    }

    for field in required_fields:
        assert field in sample_job, f"Missing field: {field}"


# ── Matcher Tests ─────────────────────────────────────────────

def test_matcher_parse_valid_json():
    """Matcher should correctly parse valid JSON responses."""
    from matching.skill_matcher import SkillMatcher
    from unittest.mock import patch, MagicMock

    with patch("matching.skill_matcher.genai"):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            matcher = SkillMatcher.__new__(SkillMatcher)
            matcher.profile = {"title": "Java Dev", "experience_years": 5,
                              "skills": ["Java"], "preferred_roles": ["Java Developer"],
                              "preferred_locations": ["Remote"],
                              "preferred_work_type": ["Full-time"],
                              "salary_min_lpa": 5,
                              "industries_preferred": [],
                              "industries_avoided": [],
                              "name": "Test User"}

            valid_json = json.dumps({
                "score": 85,
                "reasons": ["Java skill matches", "Remote work available"],
                "concerns": [],
                "summary": "Good match for Java developer"
            })

            score, reasons = matcher._parse_response(valid_json)
            assert score == 85
            assert len(reasons) > 0


def test_matcher_handles_invalid_json():
    """Matcher should handle invalid JSON gracefully."""
    from matching.skill_matcher import SkillMatcher

    matcher = SkillMatcher.__new__(SkillMatcher)
    matcher.profile = {}

    score, reasons = matcher._parse_response("invalid json response")
    assert score == 0
    assert len(reasons) > 0


# ── Bot Tests ─────────────────────────────────────────────────

def test_bot_source_emojis():
    """Source emojis should be defined for all sources."""
    from bot.telegram_bot import SOURCE_EMOJI
    assert "Jobicy" in SOURCE_EMOJI
    assert "Remotive" in SOURCE_EMOJI


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
