import sqlite3, os
DB_PATH = os.path.join(os.path.dirname(__file__), "entries.db")

week2idx = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}

idx2week = {idx: day for day, idx in week2idx.items()}

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                category TEXT NOT NULL,
                author_id TEXT NOT NULL,
                link TEXT,
                seen INTEGER DEFAULT 0
            )
        """)

def add_entry(content, category, author_id, link=None):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO entries (content, category, author_id, link) VALUES (?, ?, ?, ?)",
            (content, category, author_id, link)
        )

def get_random():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM entries WHERE seen = 0")
        (unseen_count,) = cur.fetchone()
        if unseen_count == 0:
            cur.execute("UPDATE entries SET seen = 0")
            conn.commit()
        cur.execute("""
            SELECT * FROM entries
            WHERE seen = 0
            ORDER BY RANDOM()
            LIMIT 1
        """)
        row = cur.fetchone()
        if not row:
            return None
        cur.execute(
            "UPDATE entries SET seen = 1 WHERE id = ?",
            (row["id"],)
        )
        conn.commit()
        return dict(row)

def get_by_link(content, return_row=True):
    if not content:
        return None
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM entries WHERE link = ? COLLATE NOCASE LIMIT 1",
            (content,)
        )
        row = cur.fetchone()
        if return_row:
            return dict(row) if row else None
        else:
            return row is not None
    
def get_by_entry(content, return_row=False):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM entries WHERE content = ? COLLATE NOCASE LIMIT 1",
            (content,)
        )
        row = cur.fetchone()
        if return_row:
            return dict(row) if row else None
        else:
            return row is not None

     
def delete_entry(content):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM entries WHERE content = ? COLLATE NOCASE", 
                    (content,))
        conn.commit()

def delete_db():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM entries")
        conn.commit()
