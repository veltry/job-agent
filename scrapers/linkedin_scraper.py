"""
LinkedIn Scraper - Uses Apify's LinkedIn Jobs actor to fetch job listings.
Apify free tier: ~100 results/month. Reliable, no ban risk.
"""

import logging
import hashlib
from typing import List, Dict
from apify_client import ApifyClient  # type: ignore[reportMissingImports]
from config.settings import Settings

logger = logging.getLogger(__name__)


class LinkedInScraper:
    def __init__(self):
        self.client = ApifyClient(Settings.APIFY_API_KEY)
        self.profile = Settings.get_skills_profile()

    async def fetch_jobs(self) -> List[Dict]:
        """Fetch jobs from LinkedIn via Apify actor."""
        keywords = self.profile.get("job_search_keywords", ["Software Engineer"])
        locations = self.profile.get("preferred_locations", ["India"])

        all_jobs = []

        for keyword in keywords[:3]:  # Limit to 3 keywords per scan to save quota
            for location in locations[:2]:  # Limit to 2 locations
                try:
                    jobs = await self._run_actor(keyword, location)
                    all_jobs.extend(jobs)
                    logger.info(f"  Fetched {len(jobs)} jobs for '{keyword}' in '{location}'")
                except Exception as e:
                    logger.error(f"  Failed to fetch '{keyword}' in '{location}': {e}")

        # Deduplicate by job ID
        seen_ids = set()
        unique_jobs = []
        for job in all_jobs:
            if job["id"] not in seen_ids:
                seen_ids.add(job["id"])
                unique_jobs.append(job)

        return unique_jobs[:Settings.MAX_JOBS_PER_SCAN]

    async def _run_actor(self, keyword: str, location: str) -> List[Dict]:
        """Run Apify LinkedIn jobs actor for a keyword/location pair."""
        run_input = {
            "searchKeywords": keyword,
            "location": location,
            "maxResults": 20,
            "contractType": "FULL_TIME",
        }

        run = self.client.actor(Settings.APIFY_ACTOR_ID).call(run_input=run_input)
        if not run:
            logger.warning("  Apify actor run returned no result")
            return []

        dataset_id = run.get("defaultDatasetId")
        if not dataset_id:
            logger.warning("  Apify actor run missing defaultDatasetId")
            return []

        items = list(self.client.dataset(dataset_id).iterate_items())

        return [self._normalize(item) for item in items if item]

    def _normalize(self, raw: dict) -> Dict:
        """Normalize Apify response to our internal job schema."""
        title = raw.get("title", "Unknown Role")
        company = raw.get("companyName", "Unknown Company")
        location = raw.get("location", "")

        # Generate stable ID from title+company+location
        id_str = f"{title}-{company}-{location}".lower()
        job_id = hashlib.md5(id_str.encode()).hexdigest()[:12]

        return {
            "id": job_id,
            "title": title,
            "company": company,
            "location": location,
            "description": raw.get("description", ""),
            "apply_url": raw.get("applyUrl") or raw.get("jobUrl", ""),
            "posted_at": raw.get("postedAt", ""),
            "employment_type": raw.get("employmentType", "Full-time"),
            "seniority": raw.get("seniorityLevel", ""),
            "salary": raw.get("salary", "Not disclosed"),
        }
