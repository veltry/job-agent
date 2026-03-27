import sqlite3
from typing import List

import os
THIS_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(THIS_DIR, '..', 'data', 'jobs.db')
DB_PATH = os.path.abspath(DB_PATH)

def list_pending(limit: int = 10) -> List[dict]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT id,title,company,contact_email,location,created_at FROM pending_jobs ORDER BY id DESC LIMIT ?', (limit,))
    rows = cur.fetchall()
    conn.close()
    result = []
    for r in rows:
        result.append({
            'id': r[0],
            'title': r[1],
            'company': r[2],
            'contact_email': r[3],
            'location': r[4],
            'created_at': r[5],
        })
    return result

if __name__ == '__main__':
    import json
    print(json.dumps(list_pending(5), indent=2))
