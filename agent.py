"""
Job Agent v2.0 - Main Entry Point
Scrapes multiple job sources, matches with AI, notifies via Telegram.
"""

import asyncio
import logging
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bot.telegram_bot import JobBot
from matching.skill_matcher import SkillMatcher
from scrapers.job_scraper import JobScraper
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


async def run_job_scan(bot: JobBot, scraper: JobScraper, matcher: SkillMatcher, db: Database):
    """Core pipeline: scrape → match → notify."""
    logger.info("🔍 Starting job scan...")
    try:
        jobs = await scraper.fetch_jobs()
        logger.info(f"📦 Fetched {len(jobs)} raw jobs")

        new_jobs = [j for j in jobs if not db.is_seen(j["id"])]
        logger.info(f"🆕 {len(new_jobs)} new jobs to evaluate")

        matched = 0
        for job in new_jobs:
            db.mark_seen(job["id"])
            score, reasons = await matcher.score(job)
            logger.info(f"  → {job['title']} @ {job['company']} | Score: {score}%")

            if score >= Settings.MATCH_THRESHOLD:
                await bot.send_job_card(job, score, reasons)
                matched += 1

        logger.info(f"✅ Scan complete. {matched} matches found out of {len(new_jobs)} new jobs.")

    except Exception as e:
        logger.error(f"❌ Job scan failed: {e}", exc_info=True)


async def main():
    Settings.validate()
    logger.info("🚀 Job Agent v2.0 starting up...")

    os.makedirs("logs", exist_ok=True)
    os.makedirs("storage", exist_ok=True)

    db = Database()
    scraper = JobScraper()
    matcher = SkillMatcher()
    bot = JobBot(db=db, scraper=scraper, matcher=matcher)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_job_scan,
        trigger="interval",
        hours=Settings.SCAN_INTERVAL_HOURS,
        args=[bot, scraper, matcher, db],
        id="job_scan"
    )

    await bot.start()
    scheduler.start()

    await asyncio.sleep(3)
    await run_job_scan(bot, scraper, matcher, db)

    logger.info(f"✅ Agent running. Next scan in {Settings.SCAN_INTERVAL_HOURS}h.")
    await bot.idle()


if __name__ == "__main__":
    asyncio.run(main())
