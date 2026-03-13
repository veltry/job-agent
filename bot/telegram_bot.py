"""
Telegram Bot - Sends job cards, handles user confirmations, triggers applications.
Only responds to your personal Telegram user ID for security.
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


class JobBot:
    def __init__(self, db: Database, scraper=None):
        self.db = db
        self.scraper = scraper
        self.app = Application.builder().token(Settings.TELEGRAM_BOT_TOKEN).build()
        self._register_handlers()

    def _register_handlers(self):
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CommandHandler("history", self.cmd_history))
        self.app.add_handler(CommandHandler("scan", self.cmd_scan))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))

    # ── Security: only respond to your user ID ────────────────

    def _is_authorized(self, update: Update) -> bool:
        user_id = update.effective_user.id
        if user_id != Settings.TELEGRAM_USER_ID:
            logger.warning(f"⛔ Unauthorized access attempt from user_id={user_id}")
            return False
        return True

    # ── Commands ──────────────────────────────────────────────

    async def cmd_start(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return
        await update.message.reply_text(
            "👋 *Job Agent is running!*\n\n"
            "I'll scan LinkedIn every few hours and notify you when I find matching jobs.\n\n"
            "Commands:\n"
            "/scan — Run a job scan right now\n"
            "/status — View your application stats\n"
            "/history — See all past applications\n"
            "/help — Show this message",
            parse_mode="Markdown"
        )

    async def cmd_help(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return
        await update.message.reply_text(
            "🤖 *Job Agent Commands*\n\n"
            "/scan — Trigger an immediate job scan\n"
            "/status — Application stats (total, avg score)\n"
            "/history — List all jobs you applied to\n"
            "/help — Show this help message\n\n"
            "When I find a matching job, I'll send you a card with:\n"
            "✅ Apply — Submit the application\n"
            "❌ Skip — Dismiss this job\n"
            "🔗 View — Open the job on LinkedIn",
            parse_mode="Markdown"
        )

    async def cmd_status(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return
        stats = self.db.get_application_stats()
        await update.message.reply_text(
            f"📊 *Your Application Stats*\n\n"
            f"📋 Total Applied: *{stats['total']}*\n"
            f"✅ Active: *{stats['applied']}*\n"
            f"🎯 Avg Match Score: *{stats['avg_score']}%*",
            parse_mode="Markdown"
        )

    async def cmd_history(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return
        apps = self.db.get_all_applications()
        if not apps:
            await update.message.reply_text("No applications yet.")
            return

        lines = ["📁 *Recent Applications*\n"]
        for a in apps[:10]:
            dt = a["applied_at"][:10]
            lines.append(f"• *{a['title']}* @ {a['company']}\n  📍 {a['location']} | 🎯 {a['score']}% | 📅 {dt}")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    async def cmd_scan(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return
        await update.message.reply_text("🔍 Running job scan now... I'll notify you when I find matches.")
        # Trigger scan via context (main loop handles it)
        ctx.application.create_task(self._trigger_scan())

    async def _trigger_scan(self):
        """Manually triggered scan from /scan command."""
        from matching.skill_matcher import SkillMatcher
        from agent import run_job_scan
        matcher = SkillMatcher()
        await run_job_scan(self, self.scraper, matcher, self.db)

    # ── Job Card Notification ─────────────────────────────────

    async def send_job_card(self, job: dict, score: int, reasons: list):
        """Send a formatted job card with Apply/Skip/View buttons."""
        self.db.save_pending(job, score, reasons)

        # Build match reasons text
        match_lines = "\n".join(f"  ✓ {r}" for r in reasons[:4] if not r.startswith("⚠️"))
        concern_lines = "\n".join(f"  {r}" for r in reasons if r.startswith("⚠️"))

        score_emoji = "🔥" if score >= 90 else "🎯" if score >= 75 else "👍"

        text = (
            f"{score_emoji} *Match Score: {score}%*\n\n"
            f"💼 *{job['title']}*\n"
            f"🏢 {job['company']}\n"
            f"📍 {job['location']}\n"
            f"💰 {job.get('salary', 'Not disclosed')}\n"
            f"🕐 {job.get('employment_type', 'Full-time')}"
        )

        if match_lines:
            text += f"\n\n✅ *Why it matches you:*\n{match_lines}"

        if concern_lines:
            text += f"\n\n⚠️ *Concerns:*\n{concern_lines}"

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Apply Now", callback_data=f"apply:{job['id']}"),
                InlineKeyboardButton("❌ Skip", callback_data=f"skip:{job['id']}"),
            ],
            [
                InlineKeyboardButton("🔗 View on LinkedIn", url=job["apply_url"]),
            ]
        ])

        await self.app.bot.send_message(
            chat_id=Settings.TELEGRAM_USER_ID,
            text=text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        logger.info(f"📲 Sent job card: {job['title']} @ {job['company']} ({score}%)")

    # ── Callback Handler (button presses) ─────────────────────

    async def handle_callback(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        if not self._is_authorized(update):
            await query.edit_message_text("⛔ Unauthorized.")
            return

        action, job_id = query.data.split(":", 1)

        if action == "apply":
            await self._handle_apply(query, job_id)
        elif action == "skip":
            await self._handle_skip(query, job_id)

    async def _handle_apply(self, query, job_id: str):
        job = self.db.get_pending(job_id)
        if not job:
            await query.edit_message_text("⚠️ Job details not found. It may have expired.")
            return

        # Save to applications log
        self.db.save_application(job, job["score"])
        self.db.delete_pending(job_id)

        now = datetime.now().strftime("%I:%M %p, %d %b %Y")

        await query.edit_message_text(
            f"✅ *Application Recorded!*\n\n"
            f"💼 *{job['title']}*\n"
            f"🏢 {job['company']}\n"
            f"📍 {job['location']}\n\n"
            f"🕐 Logged at: {now}\n"
            f"🔗 [Open & Apply on LinkedIn]({job['apply_url']})\n\n"
            f"_Click the link above to complete your Easy Apply on LinkedIn._",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔗 Apply on LinkedIn", url=job["apply_url"])
            ]])
        )
        logger.info(f"✅ User confirmed application: {job['title']} @ {job['company']}")

    async def _handle_skip(self, query, job_id: str):
        job = self.db.get_pending(job_id)
        self.db.delete_pending(job_id)
        title = job["title"] if job else "this job"
        await query.edit_message_text(f"❌ Skipped *{title}*.", parse_mode="Markdown")
        logger.info(f"⏭️ User skipped job_id={job_id}")

    # ── Lifecycle ─────────────────────────────────────────────

    async def start(self):
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(drop_pending_updates=True)
        logger.info("🤖 Telegram bot started and polling")

    async def idle(self):
        """Block until interrupted."""
        import asyncio
        try:
            while True:
                await asyncio.sleep(3600)
        except (KeyboardInterrupt, SystemExit):
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
