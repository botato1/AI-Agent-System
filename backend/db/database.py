# SQLite 데이터베이스 연결 관리
import sqlite3
from pathlib import Path

from backend.core.config import settings


# SQLite DB 연결을 관리하는 함수
def get_connection():
    db_path = Path(settings.SQLITE_DB_PATH)

    # storage/sqlite 폴더가 없으면 자동 생성
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    return conn


# SQLite DB 초기 테이블을 생성하는 함수
def init_db():
    conn = get_connection()
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
        source TEXT DEFAULT 'text',
        created_at TEXT NOT NULL
    )
    """)

    # 3. summaries
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS summaries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT NOT NULL,
        summary TEXT NOT NULL,
        token_count INTEGER,
        created_at TEXT NOT NULL
    )
    """)

    # 4. important_facts
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

    print("DB 생성 완료:", settings.SQLITE_DB_PATH)


if __name__ == "__main__":
    init_db()