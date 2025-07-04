# database.py
import sqlite3
from datetime import datetime

DB_FILE = "articles.db"

def setup_database():
    """Creates the database and the articles table if they don't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            url TEXT PRIMARY KEY,
            published_date TEXT
        )
    """)
    conn.commit()
    conn.close()

def is_url_processed(url):
    """Checks if a URL is already in the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT url FROM articles WHERE url = ?", (url,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def add_url_to_db(url):
    """Adds a new URL to the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO articles (url, published_date) VALUES (?, ?)", (url, datetime.now().isoformat()))
    conn.commit()
    conn.close()