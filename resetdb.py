# reset_db.py

import os
import sqlite3

DB_FILE = "articles.db"

def flush_database():
    """
    Deletes all records from the 'articles' table but keeps the table structure.
    If the database file doesn't exist, it informs the user.
    """
    if not os.path.exists(DB_FILE):
        print(f"Database file '{DB_FILE}' not found. Nothing to flush.")
        return

    try:
        print(f"Connecting to database '{DB_FILE}'...")
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        print("Flushing all records from the 'articles' table...")
        # DELETE FROM is safer than DROP TABLE as it just removes data
        cursor.execute("DELETE FROM articles")
        
        # Optional: Reset the autoincrementing counter if you have one
        # cursor.execute("DELETE FROM sqlite_sequence WHERE name='articles'")
        
        conn.commit()
        
        # Verify that the table is empty
        cursor.execute("SELECT COUNT(*) FROM articles")
        count = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"✅ Flush complete. The 'articles' table now contains {count} records.")

    except Exception as e:
        print(f"❌ An error occurred while flushing the database: {e}")

if __name__ == "__main__":
    flush_database()