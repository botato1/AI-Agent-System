# backend/db/database.py
# SQLite 데이터베이스 연결 및 초기화
import sqlite3
from pathlib import Path
from backend.core.config import settings

DB_PATH = Path(settings.SQLITE_DB_PATH)


def get_connection():
    db_path = Path(settings.SQLITE_DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # 1. conversations
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id         TEXT PRIMARY KEY,
        title      TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    # 2. messages
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id              TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        role            TEXT NOT NULL,
        content         TEXT NOT NULL,
        source          TEXT DEFAULT 'text',
        created_at      TEXT NOT NULL
    )
    """)

    # 3. summaries
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS summaries (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT NOT NULL,
        summary         TEXT NOT NULL,
        token_count     INTEGER,
        created_at      TEXT NOT NULL
    )
    """)

    # 4. important_facts
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS important_facts (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT NOT NULL,
        fact            TEXT NOT NULL,
        category        TEXT,
        created_at      TEXT NOT NULL
    )
    """)

    # 5. documents
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id               TEXT PRIMARY KEY,
        conversation_id  TEXT NOT NULL,
        title            TEXT NOT NULL,
        type             TEXT NOT NULL,
        source           TEXT NOT NULL,
        file_path        TEXT,
        json_path        TEXT DEFAULT '',
        content_markdown TEXT DEFAULT '',
        summary          TEXT,
        status           TEXT DEFAULT 'uploaded',
        notion_url       TEXT,
        error            TEXT,
        created_at       TEXT NOT NULL
    )
    """)

    # 6. tasks
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id              TEXT PRIMARY KEY,
        document_id     TEXT NOT NULL,
        conversation_id TEXT NOT NULL,
        task            TEXT NOT NULL,
        assignee        TEXT,
        deadline        TEXT,
        status          TEXT DEFAULT 'todo',
        priority        TEXT DEFAULT 'medium',
        created_at      TEXT NOT NULL
    )
    """)

    # ── 마이그레이션 (기존 DB에 컬럼 없을 때 자동 추가) ──────────
    migrations = [
        "ALTER TABLE documents ADD COLUMN json_path TEXT DEFAULT ''",
        "ALTER TABLE documents ADD COLUMN content_markdown TEXT DEFAULT ''",
        "ALTER TABLE tasks ADD COLUMN priority TEXT DEFAULT 'medium'",
    ]

    for sql in migrations:
        try:
            cursor.execute(sql)
            print(f"[migration] 적용: {sql}")
        except Exception:
            pass  # 이미 존재하면 무시

    conn.commit()
    conn.close()
    print("DB 초기화 완료:", settings.SQLITE_DB_PATH)


if __name__ == "__main__":
    init_db()