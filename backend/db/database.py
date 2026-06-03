import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DB_DIR = BASE_DIR / "storage" / "sqlite"
DB_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DB_DIR / "chat.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. conversations
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    # 2. messages
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    # 3. summaries (token_count 포함!)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS summaries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT NOT NULL,
        summary TEXT NOT NULL,
        token_count INTEGER,
        created_at TEXT NOT NULL
    )
    """)

    # 4. important_facts (category 포함!)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS important_facts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT NOT NULL,
        fact TEXT NOT NULL,
        category TEXT,
        created_at TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()

    print("DB 생성 완료:", DB_PATH)


if __name__ == "__main__":
    init_db()