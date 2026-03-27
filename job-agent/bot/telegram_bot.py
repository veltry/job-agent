"""
Lightweight integration shim for job-agent Telegram handlers.

This file simulates a minimal bot runtime for local testing. It does
NOT depend on a Telegram library — it's a plain Python harness that
invokes addjob_handler.preview_from_text and approve_pending_job while
simulating user interactions and a DB executor.

When ready, you can copy the integration bits into your real
telegram_bot.py (the comments show the minimal calls required).
"""
import sys
import os
# Ensure repository root is on sys.path for local imports
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
from bot.addjob_handler import preview_from_text, approve_pending_job, payload_to_json
import sqlite3


class SqliteExecutor:
    """Simple sqlite3-based executor for testing approve flow locally."""
    def __init__(self, path=':memory:'):
        self.conn = sqlite3.connect(path)
        self._ensure_table()

    def _ensure_table(self):
        cur = self.conn.cursor()
        cur.execute('''
        CREATE TABLE IF NOT EXISTS pending_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            company TEXT,
            contact_email TEXT,
            job_url TEXT,
            location TEXT,
            salary TEXT,
            description TEXT,
            source_raw TEXT
        )
        ''')
        self.conn.commit()

    def execute(self, query, params):
        cur = self.conn.cursor()
        cur.execute(query.replace('%s', '?'), params)
        self.conn.commit()
        return cur.lastrowid

    def cursor(self):
        return self.conn.cursor()


def simulate_message_flow(text, requester_id=5073528651):
    print('--- Received message ---')
    print(text)
    payload = preview_from_text(text, requester_id)
    print('\n--- Preview to send to user ---')
    print(payload['preview_text'])
    print('\nActions:', payload['actions'])

    # Simulate user pressing Approve
    print('\n--- Simulating Approve action (dry-run) ---')
    status = approve_pending_job(payload, db_executor=None, do_write=False)
    print(status)

    # Now simulate real DB write using sqlite executor
    print('\n--- Simulating Approve action (write to local sqlite) ---')
    db = SqliteExecutor()
    # our approve_pending_job expects either a callable or db connection
    # we'll pass a callable that wraps db.execute
    def executor_callable(query, params):
        return db.execute(query, params)

    status2 = approve_pending_job(payload, db_executor=executor_callable, do_write=True)
    print(status2)

    # Show stored record
    cur = db.conn.cursor()
    cur.execute('SELECT id, title, company, contact_email FROM pending_jobs')
    rows = cur.fetchall()
    print('\nStored rows in sqlite (id, title, company, contact_email):')
    for r in rows:
        print(r)


if __name__ == '__main__':
    sample = 'Senior SRE at Acme Inc – hr@acme.com – https://acme.com/jobs/123 – needs Kubernetes and Terraform'
    simulate_message_flow(sample)
