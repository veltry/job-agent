"""
Free‑form job‑posting extractor for Telegram messages.

Given a raw text blob (e.g., a forwarded posting or a short note),
return a dictionary with the fields needed to create a draft job:
    title, company, contact_email, job_url, location, salary_min, description

The extractor uses simple regex and heuristics; missing or ambiguous
fields are returned as None so the calling code can ask the user for
clarification.
"""
import re
from typing import Dict, Optional

# ----------------------------------------------------------------------
# Regex patterns
# ----------------------------------------------------------------------
EMAIL_RE = re.compile(r'[\w\.-]+@[\w\.-]+\.[a-z]{2,}', re.I)
# Match http/https URLs; also capture www.* without scheme (we'll add http://)
URL_RE = re.compile(r'https?://[^\s)>]+|www\.[^\s)>]+', re.I)

# Seniority / role keywords used to guess the title line
TITLE_KEYWORDS = [
    'senior', 'lead', 'manager', 'director', 'engineer', 'developer',
    'analyst', 'architect', 'specialist', 'consultant', 'officer',
    'coordinator', 'administrator', 'executive', 'chief', 'head',
    'supervisor', 'consultant', 'associate', 'assistant'
]

# Common location indicators (city, country, remote/hybrid)
LOCATION_RE = re.compile(
    r'\b(?:Remote|Hybrid|[A-Z][a-z]+(?:[, ]+[A-Z][a-z]+)*)\b'
)

# Salary patterns: numbers with optional k/K, currency symbols, ranges
SALARY_RE = re.compile(
    r'\d+[kK]?(?:\s*[-–]\s*\d+[kK]*)?\s*(?:USD|MYR|SGD|\$|RM|eur|€|£)?',
    re.I
)

# ----------------------------------------------------------------------
def extract_job_from_text(text: str) -> Dict[str, Optional[str]]:
    """
    Parse free‑form text and return a dict of job fields.

    Parameters
    ----------
    text: str
        Raw message from Telegram.

    Returns
    -------
    dict with keys:
        title, company, contact_email, job_url, location, salary_min, description
    Missing fields are set to None.
    """
    if not text or not text.strip():
        return {k: None for k in (
            'title', 'company', 'contact_email', 'job_url',
            'location', 'salary_min', 'description'
        )}

    # Normalise line endings and strip extra spaces
    raw = text.strip()
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]

    # ---------- Email ----------
    email_matches = EMAIL_RE.findall(raw)
    contact_email = email_matches[0] if len(email_matches) == 1 else None

    # ---------- URL ----------
    url_matches = URL_RE.findall(raw)
    job_url = None
    if url_matches:
        # Take the first match that looks like a job posting (could improve)
        candidate = url_matches[0]
        if candidate.startswith('www.'):
            candidate = 'http://' + candidate
        job_url = candidate

    # ---------- Title ----------
    title, company = None, None
    # Heuristics-based extraction: split title and company by patterns like "at", "@"
    for ln in lines:
        if not title:
            parts = re.split(r'\s+at\s+|\s+@\s+', ln, maxsplit=1)
            if len(parts) > 1:
                title, company = parts[0].strip(), parts[1].strip()
                break
    # Fallback for unstructured inputs
    title = title or lines[0] if lines else None

    # ---------- Company ----------
    company = None
    if title:
        # Look after the title for patterns like "at X", "@ X", " - X", " | X"
        after_title = raw.split(title, 1)[-1]
        # patterns: at <Company>, @ <Company>, dash, pipe
        m = re.search(r'\bat\s+([A-Z][a-zA-Z0-9&\s]{1,40})', after_title, re.I) \
            or re.search(r'@\s+([A-Z][a-zA-Z0-9&\s]{1,40})', after_title) \
            or re.search(r'[-|]\s+([A-Z][a-zA-Z0-9&\s]{1,40})', after_title)
        if m:
            company = m.group(1).strip()
    
    # ---------- Location ----------
    location = None
    loc_matches = LOCATION_RE.findall(raw)
    if loc_matches:
        location = next((loc for loc in loc_matches if loc.lower() not in TITLE_KEYWORDS and not loc.startswith(company) and loc.lower() not in ['kubernetes', 'terraform']), None)  # Exclude tech terms  # Filter out invalid locations like "Senior"

    # ---------- Salary ----------
    salary_min = None
    sal_matches = SALARY_RE.findall(raw)
    if sal_matches:
        salary_min = sal_matches[0]  # Take the first match (refine later)

    # ---------- Description ----------
    # Simplified description cleanup that avoids removing key fields prematurely
    cleaned_raw = raw.lower()
    for pattern in [contact_email, job_url, title, company, location, salary_min]:
        if pattern:
            cleaned_raw = cleaned_raw.replace(pattern.lower(), '')
    cleaned_raw = re.sub(r'\s{2,}', ' ', cleaned_raw.strip())
    description = re.sub(r'\b(at|–|and|with|or)\b', '', cleaned_raw).replace('–', '').strip(' ,\-') if cleaned_raw else None

    # Normalize whitespace
    description = re.sub(r'\s+', ' ', description).strip()
    # If empty, set to None
    if not description:
        description = None

    return {
        'title': title,
        'company': company,
        'contact_email': contact_email,
        'job_url': job_url,
        'location': location,
        'salary_min': salary_min,
        'description': description
    }

if __name__ == '__main__':
    sample = '''Senior SRE at Acme Inc – hr@acme.com – https://acme.com/jobs/123'''
    print(extract_job_from_text(sample))
