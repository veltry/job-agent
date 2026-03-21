# 🤖 Job Agent v2.0 — Job Search & Application Tracker

Automatically scans multiple job boards for roles matching your skills, notifies you via Telegram, and helps track your applications with cover letter generation and email sending.

---

## 🏗️ Architecture

```
⏰ Every 4 hours (configurable)
      ↓
🔍 Job Scrapers (Jobicy, Remotive, Jooble, LinkedIn)
      ↓
🤖 Gemini AI Skill Matcher (scores 0-100%)
      ↓
📲 Telegram Bot sends Job Card
      ↓
  [✅ Apply] [❌ Skip] [⭐ Save]
      ↓
  ↓ (on Apply)
📝 Cover Letter Generator
📧 Email Sender (with resume attachment)
📋 Application logged
```

---

## 📁 Project Structure

```
job-agent/
├── agent.py                   # Main entry point
├── requirements.txt
├── .env.example              # Copy to .env and fill in
├── jobagent.service          # systemd service for Oracle VM
├── config/
│   ├── settings.py            # All config & env loading
│   └── skills_profile.json   # YOUR skills — edit this first!
├── scrapers/
│   ├── job_scraper.py        # Jobicy, Remotive, Jooble APIs
│   └── linkedin_scraper.py   # Apify-based LinkedIn fetcher
├── matching/
│   └── skill_matcher.py       # Gemini AI job scoring
├── mailer/
│   ├── cover_letter.py       # Cover letter generator
│   └── email_sender.py       # Email with attachment support
├── bot/
│   └── telegram_bot.py        # Telegram bot & handlers
├── storage/
│   └── database.py            # SQLite job tracking
├── tests/
│   └── test_agent.py         # Test suite
└── logs/                     # Auto-created log files
```

---

## 🚀 Quick Setup

### 1. Get Your API Keys

| Key | Where to Get | Required |
|-----|-------------|----------|
| `TELEGRAM_BOT_TOKEN` | Message `@BotFather` on Telegram → `/newbot` | ✅ Yes |
| `TELEGRAM_USER_ID` | Message `@userinfobot` on Telegram | ✅ Yes |
| `GEMINI_API_KEY` | https://aistudio.google.com | ✅ Yes |
| `JOOBLE_API_KEY` | https://www.jooble.org/api | Optional |
| `APIFY_API_KEY` | https://apify.com | Optional |
| `SMTP_PASSWORD` | Gmail App Password (with 2FA) | Optional |

### 2. Edit Your Profile

Edit `config/skills_profile.json` with your:
- Name, title, experience
- Skills (Java, AWS, etc.)
- Target roles & locations
- Minimum salary
- Job search keywords

### 3. Install & Run

```bash
# Clone repo
git clone https://github.com/veltry/job-agent.git
cd job-agent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and edit env
cp .env.example .env
nano .env   # Fill in your API keys

# Run
python agent.py
```

### 4. Setup System Service

```bash
sudo cp jobagent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable jobagent
sudo systemctl start jobagent
```

---

## 📲 Telegram Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/scan` | Trigger immediate job scan |
| `/status` | View application stats |
| `/history` | See past applications |
| `/stats` | Detailed statistics |
| `/cover <job_id>` | Generate cover letter |
| `/email <job_id> <email>` | Send cover letter + resume |
| `/help` | Show all commands |

---

## 📧 Email Features

The agent can send application emails with:
- **Personalized cover letter** (AI-generated from job + profile)
- **Resume PDF attachment**
- **Gmail SMTP** (or any SMTP server)

### Setup Gmail SMTP

1. Enable 2-Factor Authentication on your Google account
2. Go to https://myaccount.google.com/apppasswords
3. Generate an App Password for "Mail"
4. Add to `.env`:
   ```
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your_email@gmail.com
   SMTP_PASSWORD=xxxx_xxxx_xxxx_xxxx
   FROM_EMAIL=your_email@gmail.com
   ```

---

## 🔍 Job Sources

| Source | Coverage | API Key Required |
|--------|----------|------------------|
| **Jobicy** | Remote tech jobs | ❌ No |
| **Remotive** | Remote jobs | ❌ No |
| **Jooble** | Asia/Singapore/Malaysia | ✅ Yes (free) |
| **LinkedIn** | All jobs | ✅ Yes (Apify) |

---

## 💰 Running Costs

| Service | Cost |
|---------|------|
| Oracle Cloud VM | **Free** (always-free tier) |
| Jobicy, Remotive | **Free** |
| Jooble API | **Free** |
| Gemini AI | **~$1-2/month** (very low usage) |
| Telegram Bot | **Free** |
| **Total** | **~$1-2/month** |

---

## 🔒 Security

- Bot **only responds to your Telegram ID** — all others ignored
- API keys in `.env` — **never committed to git**
- `.gitignore` excludes: `.env`, `logs/`, `storage/jobs.db`, `venv/`
- SSH key auth only for VM access

---

## 🧪 Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_agent.py::test_database_creates -v
```

---

## 📈 CI/CD Pipeline

Push to `feature/job-agent` → Create PR → Merge to `main` → Auto-deploy to Oracle VM

GitHub Actions:
1. **Test** — Runs pytest
2. **Deploy** — SSH to VM, pull code, restart service
3. **Notify** — Telegram message on success/failure

---

## 🛠️ Troubleshooting

**Bot not responding?**
```bash
# Check service
sudo systemctl status jobagent

# View logs
sudo journalctl -u jobagent -f
```

**No jobs found?**
- Check `JOOBLE_API_KEY` or `APIFY_API_KEY`
- Update `job_search_keywords` in skills_profile.json
- Run `/scan` manually to see logs

**Email not sending?**
- Verify Gmail App Password is correct
- Check SMTP settings in `.env`

---

_Last updated: 2026-03-21_
