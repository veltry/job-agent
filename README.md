# 🤖 Job Agent — LinkedIn → Telegram Job Notifier

Automatically scans LinkedIn for jobs matching your skills, sends you a Telegram notification, and logs your applications when you confirm.

---

## 🏗️ Architecture

```
⏰ Every 4 hours
      ↓
🔍 LinkedIn Scraper (via Apify)
      ↓
🤖 Claude AI Skill Matcher
      ↓
📲 Telegram Bot sends Job Card
      ↓
  [✅ Apply] [❌ Skip] [🔗 View]
      ↓
✅ Application logged + LinkedIn link opened
```

---

## 📁 Project Structure

```
job-agent/
├── agent.py                   # Main entry point
├── requirements.txt
├── .env.example               # Copy to .env and fill in
├── jobagent.service           # systemd service for Oracle VM
├── config/
│   ├── settings.py            # All config & env loading
│   └── skills_profile.json    # YOUR skills — edit this first!
├── scrapers/
│   └── linkedin_scraper.py    # Apify-based LinkedIn fetcher
├── matching/
│   └── skill_matcher.py       # Claude AI job scoring
├── bot/
│   └── telegram_bot.py        # Telegram bot & handlers
├── storage/
│   └── database.py            # SQLite job tracking
└── logs/                      # Auto-created log files
```

---

## 🚀 Setup Guide

### Step 1 — Get Your API Keys

| Key | Where to Get |
|-----|-------------|
| `TELEGRAM_BOT_TOKEN` | Message `@BotFather` on Telegram → `/newbot` |
| `TELEGRAM_USER_ID` | Message `@userinfobot` on Telegram |
| `CLAUDE_API_KEY` | https://console.anthropic.com |
| `APIFY_API_KEY` | https://apify.com (free account) |

### Step 2 — Edit Your Skills Profile

Open `config/skills_profile.json` and update:
- Your skills list
- Preferred roles and locations
- Minimum salary
- Job search keywords

### Step 3 — Setup on Oracle Cloud VM

```bash
# SSH into your Oracle VM
ssh ubuntu@<your-vm-ip>

# Clone your repo
git clone https://github.com/your-username/job-agent.git
cd job-agent

# Install dependencies
pip3 install -r requirements.txt

# Create .env from template
cp .env.example .env
nano .env   # Fill in your API keys

# Test run
python3 agent.py
```

### Step 4 — Run as a System Service (Always-On)

```bash
# Copy service file
sudo cp jobagent.service /etc/systemd/system/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable jobagent
sudo systemctl start jobagent

# Verify it's running
sudo systemctl status jobagent

# Watch live logs
sudo journalctl -u jobagent -f
```

### Step 5 — Auto-Deploy from GitHub (Optional)

1. Push your code to GitHub (make sure `.env` is in `.gitignore`!)
2. Add these GitHub Secrets in your repo settings:
   - `ORACLE_VM_IP` — your VM's public IP
   - `ORACLE_SSH_KEY` — your private SSH key content
3. Every push to `main` will auto-deploy to your VM

---

## 📲 Telegram Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/scan` | Trigger an immediate job scan |
| `/status` | View application stats |
| `/history` | See past 10 applications |
| `/help` | Show all commands |

---

## 🔒 Security Notes

- The bot **only responds to your Telegram user ID** — all other users are ignored
- API keys are stored in `.env` — never committed to git
- `.gitignore` excludes `.env`, `logs/`, and `storage/jobs.db`
- SSH key authentication only (no password login on VM)

---

## 💰 Running Costs

| Service | Cost |
|---------|------|
| Oracle Cloud VM | **Free forever** |
| Apify (LinkedIn scraper) | **Free** (~100 results/month free tier) |
| Claude API | ~$0.01–0.05/scan (very low) |
| Telegram Bot API | **Free** |
| **Total** | **~$1–2/month** (Claude API only) |

---

## 🛠️ Customization

- **Change scan frequency**: Edit `SCAN_INTERVAL_HOURS` in `config/settings.py`
- **Change match threshold**: Edit `MATCH_THRESHOLD` (default: 70%)
- **Add more job sources**: Extend `scrapers/` with new scraper classes
- **Track application status**: Update `status` field in DB after interviews
