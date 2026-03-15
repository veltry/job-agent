"""
Job Scraper v2 - Fetches from multiple free sources:
  1. Jobicy API  - Remote tech jobs
  2. Remotive API - Remote jobs
"""

import logging
import hashlib
import urllib.request
import urllib.parse
import json
from typing import List, Dict
from config.settings import Settings

logger = logging.getLogger(__name__)


class JobScraper:
    def __init__(self):
        self.profile = Settings.get_skills_profile()

    async def fetch_jobs(self) -> List[Dict]:
        """Fetch jobs from all sources and merge results."""
        all_jobs = []

        # Source 1: Jobicy
        jobicy_jobs = await self._fetch_jobicy()
        all_jobs.extend(jobicy_jobs)
        logger.info(f"📌 Jobicy: {len(jobicy_jobs)} jobs")

        # Source 2: Remotive
        remotive_jobs = await self._fetch_remotive()
        all_jobs.extend(remotive_jobs)
        logger.info(f"📌 Remotive: {len(remotive_jobs)} jobs")

        # Deduplicate by ID
        seen_ids = set()
        unique_jobs = []
        for job in all_jobs:
            if job["id"] not in seen_ids:
                seen_ids.add(job["id"])
                unique_jobs.append(job)

        logger.info(f"📦 Total unique jobs: {len(unique_jobs)}")
        return unique_jobs[:Settings.MAX_JOBS_PER_SCAN]

    # ── Source 1: Jobicy ──────────────────────────────────────

    async def _fetch_jobicy(self) -> List[Dict]:
        keywords = self.profile.get("job_search_keywords", ["Java developer"])
        all_jobs = []

        for keyword in keywords[:3]:
            try:
                tag = keyword.split()[0].lower()
                params = urllib.parse.urlencode({"count": 20, "tag": tag})
                url = f"https://jobicy.com/api/v2/remote-jobs?{params}"

                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read())

                for item in data.get("jobs", []):
                    job_id = "jobicy_" + hashlib.md5(
                        str(item.get("id", "")).encode()
                    ).hexdigest()[:10]

                    all_jobs.append({
                        "id": job_id,
                        "source": "Jobicy",
                        "title": item.get("jobTitle", ""),
                        "company": item.get("companyName", ""),
                        "location": item.get("jobGeo", "Remote"),
                        "description": item.get("jobExcerpt", ""),
                        "apply_url": item.get("url", ""),
                        "posted_at": item.get("pubDate", ""),
                        "employment_type": item.get("jobType", "Full-time"),
                        "salary": str(item.get("annualSalaryMin", "Not disclosed")),
                    })

                logger.info(f"  Jobicy '{keyword}': {len(data.get('jobs', []))} jobs")

            except Exception as e:
                logger.error(f"  Jobicy failed for '{keyword}': {e}")

        return all_jobs

    # ── Source 2: Remotive ────────────────────────────────────

    async def _fetch_remotive(self) -> List[Dict]:
        keywords = self.profile.get("job_search_keywords", ["Java"])
        all_jobs = []

        for keyword in keywords[:2]:
            try:
                params = urllib.parse.urlencode({"search": keyword, "limit": 20})
                url = f"https://remotive.com/api/remote-jobs?{params}"

                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read())

                for item in data.get("jobs", []):
                    job_id = "remotive_" + hashlib.md5(
                        str(item.get("id", "")).encode()
                    ).hexdigest()[:10]

                    all_jobs.append({
                        "id": job_id,
                        "source": "Remotive",
                        "title": item.get("title", ""),
                        "company": item.get("company_name", ""),
                        "location": item.get("candidate_required_location", "Remote"),
                        "description": item.get("description", "")[:1500],
                        "apply_url": item.get("url", ""),
                        "posted_at": item.get("publication_date", ""),
                        "employment_type": item.get("job_type", "Full-time"),
                        "salary": item.get("salary", "Not disclosed") or "Not disclosed",
                    })

                logger.info(f"  Remotive '{keyword}': {len(data.get('jobs', []))} jobs")

            except Exception as e:
                logger.error(f"  Remotive failed for '{keyword}': {e}")

        return all_jobs
