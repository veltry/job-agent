"""
Job Agent - Main Entry Point
Scrapes LinkedIn jobs, matches with your skills using Claude AI,
sends notifications via Telegram, and handles applications.
"""

import asyncio
import logging
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bot.telegram_bot import JobBot
from matching.skill_matcher import SkillMatcher
from scrapers.linkedin_scraper import LinkedInScraper
from storage.database import Database
from config.settings import Settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("logs/agent.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def run_job_scan(bot: JobBot, scraper: LinkedInScraper, matcher: SkillMatcher, db: Database):
    """Core pipeline: scrape → match → notify."""
    logger.info("🔍 Starting job scan...")
    try:
        jobs = await scraper.fetch_jobs()
        logger.info(f"📦 Fetched {len(jobs)} raw jobs from LinkedIn")

        new_jobs = [j for j in jobs if not db.is_seen(j["id"])]
        logger.info(f"🆕 {len(new_jobs)} new jobs to evaluate")

        for job in new_jobs:
            db.mark_seen(job["id"])
            score, reasons = await matcher.score(job)
            logger.info(f"  → {job['title']} @ {job['company']} | Score: {score}%")

            if score >= Settings.MATCH_THRESHOLD:
                await bot.send_job_card(job, score, reasons)

    except Exception as e:
        logger.error(f"❌ Job scan failed: {e}", exc_info=True)


async def main():
    logger.info("🚀 Job Agent starting up...")

    # Init components
    db = Database()
    scraper = LinkedInScraper()
    matcher = SkillMatcher()
    bot = JobBot(db=db, scraper=scraper)

    # Schedule periodic scans
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_job_scan,
        trigger="interval",
        hours=Settings.SCAN_INTERVAL_HOURS,
        args=[bot, scraper, matcher, db],
        id="job_scan",
        next_run_time=None  # Don't run immediately, wait for bot to start
    )

    # Start bot and scheduler
    await bot.start()
    scheduler.start()

    # Run first scan after a short delay
    await asyncio.sleep(3)
    await run_job_scan(bot, scraper, matcher, db)

    logger.info(f"✅ Agent running. Next scan in {Settings.SCAN_INTERVAL_HOURS}h. Waiting for Telegram messages...")

    # Keep running
    await bot.idle()


if __name__ == "__main__":
    asyncio.run(main())
