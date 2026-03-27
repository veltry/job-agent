#!/usr/bin/env bash
set -euo pipefail
REQ_USER="$1"
REQ_HOST="$2"
KEY_PATH="$3"
LOGFILE="migration.log"

echo "Starting migration run against ${REQ_USER}@${REQ_HOST}" | tee $LOGFILE
ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no ${REQ_USER}@${REQ_HOST} <<'SSH' | tee -a ../migration.log
set -e
cd ~/job-agent
mkdir -p backups
TS=$(date +"%Y%m%d-%H%M%S")
if [ -f data/jobs.db ]; then
  cp data/jobs.db backups/jobs.db.backup-${TS}
  echo "Backup created: backups/jobs.db.backup-${TS}"
else
  echo "No data/jobs.db found; skipping backup"
fi
for f in migrations/*.sql; do
  echo "Applying migration: $f"
  sqlite3 data/jobs.db < "$f" || { echo "Migration failed: $f"; exit 2; }
done
echo "Migrations applied"
sqlite3 data/jobs.db "PRAGMA table_info('pending_jobs');"
SSH

echo "Migration run complete" | tee -a $LOGFILE
