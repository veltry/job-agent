"""
Telegram Bot v2 - Enhanced job cards, better UX, deploy notifications.
"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes
)
from config.settings import Settings
from storage.database import Database

logger = logging.getLogger(__name__)

SOURCE_EMOJI = {
    "Jobicy": "🟢",
    "Remotive": "🔵",
    "LinkedIn": "🔷",
    "Jooble": "🟠",
    "Indeed": "🟡",
}


class JobBot:
    def __init__(self, db: Database, scraper=None, matcher=None):
        self.db = db
        self.scraper = scraper
        self.matcher = matcher
        self.app = Application.builder().token(Settings.TELEGRAM_BOT_TOKEN).build()
        self._register_handlers()

    def _register_handlers(self):
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CommandHandler("history", self.cmd_history))
        self.app.add_handler(CommandHandler("scan", self.cmd_scan))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("stats", self.cmd_stats))
        self.app.add_handler(CommandHandler("cover", self.cmd_cover))
        self.app.add_handler(CommandHandler("email", self.cmd_email))
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))

    # ── Security ──────────────────────────────────────────────

    def _is_authorized(self, update: Update) -> bool:
        if update.effective_user is None:
            logger.warning("⛔ Unauthorized access: missing effective_user")
            return False

        user_id = update.effective_user.id
        if user_id != Settings.TELEGRAM_USER_ID:
            logger.warning(f"⛔ Unauthorized access from user_id={user_id}")
            return False
        return True

    async def _reply(self, update: Update, text: str, **kwargs):
        message = update.effective_message
        if message is None:
            logger.warning("Cannot reply: update has no effective_message")
            return
        await message.reply_text(text, **kwargs)

    # ── Commands ──────────────────────────────────────────────

    async def cmd_start(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return
        await self._reply(
            update,
            "👋 *Job Agent v2.0 is running!*\n\n"
            "I scan multiple job boards every few hours and notify you of matches.\n\n"
            "📋 *Sources:* Jobicy, Remotive\n"
            "🤖 *AI:* Gemini 2.0 Flash\n\n"
            "*Commands:*\n"
            "/scan — Run a job scan now\n"
            "/status — View application stats\n"
            "/history — See past applications\n"
            "/stats — Detailed statistics\n"
            "/help — Show all commands",
            parse_mode="Markdown"
        )

    async def cmd_help(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return
        await self._reply(
            update,
            "🤖 *Job Agent v2.0 Commands*\n\n"
            "/scan — Trigger immediate job scan\n"
            "/status — Application stats\n"
            "/history — Last 10 applications\n"
            "/stats — Detailed breakdown\n"
            "/cover <job_id> — Generate cover letter\n"
            "/email <job_id> <email> — Send cover letter + resume\n"
            "/help — This message\n\n"
            "*Job Card Buttons:*\n"
            "✅ Apply — Log & open job link\n"
            "❌ Skip — Dismiss job\n"
            "🔗 View — Open on job board\n"
            "⭐ Save — Save for later",
            parse_mode="Markdown"
        )

    async def cmd_status(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return
        stats = self.db.get_application_stats()
        await self._reply(
            update,
            f"📊 *Application Stats*\n\n"
            f"📋 Total Applied: *{stats['total']}*\n"
            f"✅ Active: *{stats['applied']}*\n"
            f"🎯 Avg Match Score: *{stats['avg_score']}%*\n"
            f"🏆 Best Score: *{stats['best_score']}%*",
            parse_mode="Markdown"
        )

    async def cmd_stats(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return
        stats = self.db.get_detailed_stats()
        await self._reply(
            update,
            f"📈 *Detailed Statistics*\n\n"
            f"*Applications:*\n"
            f"  Total: {stats['total']}\n"
            f"  This week: {stats['this_week']}\n"
            f"  Avg score: {stats['avg_score']}%\n\n"
            f"*By Source:*\n"
            f"  🟢 Jobicy: {stats.get('jobicy', 0)}\n"
            f"  🔵 Remotive: {stats.get('remotive', 0)}\n"
            f"  🔷 LinkedIn: {stats.get('linkedin', 0)}\n"
            f"  🟠 Jooble: {stats.get('jooble', 0)}\n\n"
            f"*Jobs Seen Total:* {stats['total_seen']}",
            parse_mode="Markdown"
        )

    async def cmd_history(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return
        apps = self.db.get_all_applications()
        if not apps:
            await self._reply(update, "No applications yet.")
            return

        lines = ["📁 *Recent Applications*\n"]
        for a in apps[:10]:
            dt = a["applied_at"][:10]
            source_emoji = SOURCE_EMOJI.get(a.get("source", ""), "📌")
            lines.append(
                f"{source_emoji} *{a['title']}* @ {a['company']}\n"
                f"  📍 {a['location']} | 🎯 {a['score']}% | 📅 {dt}"
            )

        await self._reply(update, "\n".join(lines), parse_mode="Markdown")

    async def cmd_scan(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return
        await self._reply(
            update,
            "🔍 *Running job scan now...*\n"
            "I'll notify you when I find matches!",
            parse_mode="Markdown"
        )
        ctx.application.create_task(self._trigger_scan())

    async def _trigger_scan(self):
        from agent import run_job_scan

        if self.scraper is None or self.matcher is None:
            logger.error("Cannot run manual scan: scraper/matcher not initialized")
            return

        await run_job_scan(self, self.scraper, self.matcher, self.db)

    # ── Cover Letter & Email Commands ────────────────────────

    async def cmd_cover(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """Generate cover letter for a saved job."""
        if not self._is_authorized(update):
            return
        
        args = ctx.args
        if not args:
            await self._reply(
                update,
                "📝 *Generate Cover Letter*\n\n"
                "Usage: /cover <job_id>\n\n"
                "Find job_id from /history",
                parse_mode="Markdown"
            )
            return
        
        job_id = args[0]
        job = self.db.get_pending(job_id)
        
        if not job:
            # Try to get from applications
            apps = self.db.get_all_applications()
            job = next((a for a in apps if a.get("job_id") == job_id), None)
        
        if not job:
            await self._reply(update, "❌ Job not found. Use /history to see job IDs.")
            return
        
        try:
            from mailer.cover_letter import CoverLetterGenerator
            profile = Settings.get_skills_profile()
            generator = CoverLetterGenerator(profile)
            cover_letter = generator.generate(job)
            
            # Save to file
            from pathlib import Path
            output_dir = Path("storage/cover_letters")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"cover_letter_{job_id}.txt"
            
            with open(output_path, 'w') as f:
                f.write(cover_letter)
            
            await self._reply(
                update,
                f"✅ *Cover Letter Generated!*\n\n"
                f"📄 {job.get('title')} @ {job.get('company')}\n\n"
                f"Saved to: `{output_path}`\n\n"
                f"To send via email:\n"
                f"/email {job_id} hr@company.com",
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Error generating cover letter: {e}")
            await self._reply(update, f"❌ Error: {str(e)}")

    async def cmd_email(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """Send cover letter + resume via email."""
        if not self._is_authorized(update):
            return
        
        args = ctx.args
        if len(args) < 2:
            await self._reply(
                update,
                "📧 *Send Application Email*\n\n"
                "Usage: /email <job_id> <to_email>\n\n"
                "Example: /email job_123 hr@company.com\n\n"
                "Attaches cover letter + resume from config.",
                parse_mode="Markdown"
            )
            return
        
        job_id = args[0]
        to_email = args[1]
        
        job = self.db.get_pending(job_id)
        if not job:
            # Try applications
            apps = self.db.get_all_applications()
            job = next((a for a in apps if a.get("job_id") == job_id), None)
        
        if not job:
            await self._reply(update, "❌ Job not found. Use /history to see job IDs.")
            return
        
        await self._reply(
            update,
            f"📧 *Sending email...*\n\n"
            f"To: {to_email}\n"
            f"Job: {job.get('title')} @ {job.get('company')}",
            parse_mode="Markdown"
        )
        
        try:
            from mailer.cover_letter import CoverLetterGenerator
            from mailer.email_sender import create_email_sender
            import os
            
            # Get profile and generate cover letter
            profile = Settings.get_skills_profile()
            generator = CoverLetterGenerator(profile)
            cover_letter = generator.generate(job)
            
            # Create email sender from env
            env_vars = {
                "SMTP_HOST": os.getenv("SMTP_HOST", "smtp.gmail.com"),
                "SMTP_PORT": os.getenv("SMTP_PORT", "587"),
                "SMTP_USER": os.getenv("SMTP_USER", ""),
                "SMTP_PASSWORD": os.getenv("SMTP_PASSWORD", ""),
                "FROM_EMAIL": os.getenv("FROM_EMAIL", os.getenv("SMTP_USER", "")),
            }
            
            email_sender = create_email_sender(env_vars)
            
            # Get resume path
            resume_path = Path("config/resume.pdf")
            
            # Send email
            success = email_sender.send_with_cover_letter(
                to_email=to_email,
                job=job,
                cover_letter=cover_letter,
                resume_path=resume_path if resume_path.exists() else None
            )
            
            if success:
                await self._reply(
                    update,
                    f"✅ *Email Sent Successfully!*\n\n"
                    f"To: {to_email}\n"
                    f"Job: {job.get('title')} @ {job.get('company')}",
                    parse_mode="Markdown"
                )
            else:
                await self._reply(
                    update,
                    "❌ *Failed to send email.*\n\n"
                    "Check SMTP settings in .env",
                    parse_mode="Markdown"
                )
                
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            await self._reply(update, f"❌ Error: {str(e)}")

    # ── Job Card ──────────────────────────────────────────────

    async def send_job_card(self, job: dict, score: int, reasons: list):
        """Send enhanced job card with source, score breakdown and buttons."""
        self.db.save_pending(job, score, reasons)

        source = job.get("source", "Unknown")
        source_emoji = SOURCE_EMOJI.get(source, "📌")

        # Score badge
        if score >= 90:
            score_badge = "🔥 Excellent"
        elif score >= 80:
            score_badge = "🎯 Strong"
        elif score >= 70:
            score_badge = "👍 Good"
        else:
            score_badge = "🤔 Possible"

        # Match reasons (exclude concerns)
        match_lines = "\n".join(
            f"  ✓ {r}" for r in reasons[:3]
            if not r.startswith("⚠️") and not r.startswith("💡")
        )

        # Summary line
        summary = next((r for r in reasons if r.startswith("💡")), "")

        # Concerns
        concerns = [r for r in reasons if r.startswith("⚠️")]
        concern_lines = "\n".join(f"  {c}" for c in concerns[:2])

        text = (
            f"{source_emoji} *{source}* | {score_badge}: *{score}%*\n\n"
            f"💼 *{job['title']}*\n"
            f"🏢 {job['company']}\n"
            f"📍 {job['location']}\n"
            f"💰 {job.get('salary', 'Not disclosed')}\n"
            f"🕐 {job.get('employment_type', 'Full-time')}"
        )

        if match_lines:
            text += f"\n\n✅ *Why it matches:*\n{match_lines}"

        if summary:
            text += f"\n\n{summary}"

        if concern_lines:
            text += f"\n\n{concern_lines}"

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Apply", callback_data=f"apply:{job['id']}"),
                InlineKeyboardButton("❌ Skip", callback_data=f"skip:{job['id']}"),
                InlineKeyboardButton("⭐ Save", callback_data=f"save:{job['id']}"),
            ],
            [
                InlineKeyboardButton("🔗 View Job", url=job["apply_url"]),
            ]
        ])

        await self.app.bot.send_message(
            chat_id=Settings.TELEGRAM_USER_ID,
            text=text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        logger.info(f"📲 Sent: {job['title']} @ {job['company']} ({score}%)")

    # ── Deploy Notification ───────────────────────────────────

    async def send_deploy_notification(self, version: str, status: str, details: str = ""):
        """Send CI/CD deployment notification."""
        emoji = "✅" if status == "success" else "❌"
        text = (
            f"{emoji} *Deployment {status.upper()}*\n\n"
            f"🔖 Version: `{version}`\n"
            f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        if details:
            text += f"\n📋 Details: {details}"

        await self.app.bot.send_message(
            chat_id=Settings.TELEGRAM_USER_ID,
            text=text,
            parse_mode="Markdown"
        )

    # ── Callback Handler ──────────────────────────────────────

    async def handle_callback(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if query is None:
            logger.warning("Callback received without callback_query")
            return

        await query.answer()

        if not self._is_authorized(update):
            await query.edit_message_text("⛔ Unauthorized.")
            return

        if not query.data:
            await query.edit_message_text("⚠️ Invalid action.")
            return

        action, job_id = query.data.split(":", 1)

        if action == "apply":
            await self._handle_apply(query, job_id)
        elif action == "skip":
            await self._handle_skip(query, job_id)
        elif action == "save":
            await self._handle_save(query, job_id)

    async def _handle_apply(self, query, job_id: str):
        job = self.db.get_pending(job_id)
        if not job:
            await query.edit_message_text("⚠️ Job details expired.")
            return

        self.db.save_application(job, job["score"])
        self.db.delete_pending(job_id)

        now = datetime.now().strftime("%I:%M %p, %d %b %Y")
        source_emoji = SOURCE_EMOJI.get(job.get("source", ""), "📌")

        await query.edit_message_text(
            f"✅ *Application Logged!*\n\n"
            f"{source_emoji} *{job['title']}*\n"
            f"🏢 {job['company']}\n"
            f"📍 {job['location']}\n"
            f"🎯 Match Score: {job['score']}%\n"
            f"🕐 Logged: {now}\n\n"
            f"👆 Click below to complete your application:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔗 Open & Apply", url=job["apply_url"])
            ]])
        )
        logger.info(f"✅ Applied: {job['title']} @ {job['company']}")

    async def _handle_skip(self, query, job_id: str):
        job = self.db.get_pending(job_id)
        self.db.delete_pending(job_id)
        title = job["title"] if job else "this job"
        company = job["company"] if job else ""
        await query.edit_message_text(
            f"❌ *Skipped*\n_{title}_ @ {company}",
            parse_mode="Markdown"
        )

    async def _handle_save(self, query, job_id: str):
        job = self.db.get_pending(job_id)
        if not job:
            await query.edit_message_text("⚠️ Job details expired.")
            return
        self.db.save_for_later(job_id)
        await query.answer("⭐ Saved for later!", show_alert=True)

    # ── Lifecycle ─────────────────────────────────────────────

    async def start(self):
        await self.app.initialize()
        await self.app.start()
        if self.app.updater is not None:
            await self.app.updater.start_polling(drop_pending_updates=True)
        logger.info("🤖 Telegram bot started")

    async def idle(self):
        import asyncio
        try:
            while True:
                await asyncio.sleep(3600)
        except (KeyboardInterrupt, SystemExit):
            if self.app.updater is not None:
                await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
