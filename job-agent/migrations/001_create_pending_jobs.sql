-- Migration: create pending_jobs table
-- Idempotent: safe to run multiple times

CREATE TABLE IF NOT EXISTS pending_jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  company TEXT NOT NULL,
  contact_email TEXT,
  job_url TEXT,
  location TEXT,
  salary TEXT,
  description TEXT,
  source_raw TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

-- Optional index for job_url uniqueness (uncomment if desired)
-- CREATE UNIQUE INDEX IF NOT EXISTS pending_jobs_job_url_idx ON pending_jobs (job_url);
