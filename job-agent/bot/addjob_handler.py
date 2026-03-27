"""
Helper handlers for job-agent Telegram bot integration.

This module provides a small, framework-agnostic API so the existing
`telegram_bot.py` can call into it without heavy coupling to a
particular telegram library. The functions here are pure-Python and
non-destructive by default (DB write is behind an explicit function).

Usage (example integration snippet to place in telegram_bot.py):

from job_agent.bot.addjob_handler import preview_from_text, approve_pending_job

# when text message arrives:
parsed = preview_from_text(text, requester_id)
# send parsed['preview_text'] to user with Approve/Edit/Cancel buttons

# on Approve callback:
approve_pending_job(parsed, db_conn, do_write=True)  # requires DB connection

"""
from typing import Dict, Optional
from utils.extract_job import extract_job_from_text
import json


def preview_from_text(text: str, requester_id: Optional[int] = None) -> Dict:
    """Parse free-form job text and return a preview payload.

    The preview payload contains:
      - parsed: the raw dict from extract_job
      - preview_text: human-readable preview suitable for sending to Telegram
      - actions: suggested inline actions (Approve/Edit/Cancel)
      - metadata: requester id and original text

    This function is safe to call in the bot process.
    """
    parsed = extract_job_from_text(text)
    # Build preview text
    lines = []
    def add(k, v):
        lines.append(f"{k}: {v if v is not None else '—'}")
    add('Title', parsed.get('title'))
    add('Company', parsed.get('company'))
    add('Contact Email', parsed.get('contact_email'))
    add('Job URL', parsed.get('job_url'))
    add('Location', parsed.get('location'))
    add('Salary', parsed.get('salary_min'))
    add('Description', parsed.get('description'))

    preview_text = "\n".join(lines)

    payload = {
        'parsed': parsed,
        'preview_text': preview_text,
        'actions': ['approve', 'edit', 'cancel'],
        'metadata': {
            'requester_id': requester_id,
            'original_text': text
        }
    }
    return payload


def approve_pending_job(payload: Dict, db_executor=None, do_write: bool = False) -> Dict:
    """Approve a parsed job payload and optionally write to DB.

    Parameters
    - payload: dict returned by preview_from_text
    - db_executor: a callable(db_query:str, params:tuple) -> result OR a DB connection
                   If None and do_write=True, the function will raise.
    - do_write: if True, attempt to write to DB. Default False.

    Returns a status dict with keys: success(bool), message(str), record_id(optional)
    """
    parsed = payload.get('parsed', {})

    # Minimal validation
    if not parsed.get('title') or not parsed.get('company'):
        return {'success': False, 'message': 'Missing required fields (title/company)'}

    if do_write:
        if db_executor is None:
            return {'success': False, 'message': 'DB executor not provided; refusing to write'}
        # We'll attempt to insert into a table `pending_jobs` with known columns.
        try:
            # Default query uses numbered placeholders for psycopg2 (%s). If the executor
            # is a sqlite wrapper that expects '?', it should handle replacement itself.
            query = ("INSERT INTO pending_jobs (title, company, contact_email, job_url, location, salary, description, source_raw)"
                     " VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id")
            params = (
                parsed.get('title'), parsed.get('company'), parsed.get('contact_email'),
                parsed.get('job_url'), parsed.get('location'), parsed.get('salary_min'),
                parsed.get('description'), payload.get('metadata', {}).get('original_text')
            )

            # If db_executor is a callable, we expect it to accept (query, params)
            # and return an integer record id. This keeps the write path consistent
            # across different DB backends.
            if callable(db_executor):
                record_id = db_executor(query, params)
                return {'success': True, 'message': 'Job saved', 'record_id': record_id}

            # If db_executor is a DB connection-like object with cursor/commit
            cur = db_executor.cursor()
            cur.execute(query, params)
            # Try to fetch the returned id (Postgres). If none, attempt to get lastrowid.
            try:
                record_id = cur.fetchone()[0]
            except Exception:
                # Fallback: some adapters (sqlite) don't support RETURNING; use lastrowid
                record_id = getattr(cur, 'lastrowid', None)
            db_executor.commit()
            return {'success': True, 'message': 'Job saved', 'record_id': record_id}

        except Exception as e:
            # Return a clear error message for the caller to interpret.
            return {'success': False, 'message': f'DB write failed: {e}'}

    # If not writing, return a dry-run success
    return {'success': True, 'message': 'Dry-run: parsed successfully', 'record_id': None}


# Helper to pretty-print payload for debugging
def payload_to_json(payload: Dict) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False)
