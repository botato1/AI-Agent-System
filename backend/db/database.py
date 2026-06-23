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

    # 현재 프로젝트는 FK 강제 정책을 전체적으로 통일하지 않았으므로 보류
    # 필요 시 전체 DB 정책 확정 후 아래 옵션 사용
    # conn.execute("PRAGMA foreign_keys = ON")

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
    # chroma_status: ChromaDB 적재 상태
    #   pending → 적재 대기 (업로드 직후 기본값)
    #   success → 적재 완료 (검색 가능)
    #   failed  → 적재 실패 (재시도 필요)
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
        chroma_status    TEXT DEFAULT 'pending',
        notion_url       TEXT,
        error            TEXT,
        metadata         TEXT DEFAULT '{}',
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

    # 7. document_chunks
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS document_chunks (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id  TEXT NOT NULL,
        chunk_index  INTEGER NOT NULL,
        content      TEXT NOT NULL,
        start_time   REAL,
        end_time     REAL,
        speaker      TEXT,
        content_type TEXT DEFAULT 'transcription',
        user_edited  INTEGER DEFAULT 0,
        created_at   TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (document_id) REFERENCES documents(id)
    )
    """)

    # ── 마이그레이션 (기존 DB에 컬럼 없을 때 자동 추가) ────
    migrations = [
        "ALTER TABLE documents ADD COLUMN json_path TEXT DEFAULT ''",
        "ALTER TABLE documents ADD COLUMN content_markdown TEXT DEFAULT ''",
        "ALTER TABLE documents ADD COLUMN metadata TEXT DEFAULT '{}'",
        "ALTER TABLE tasks ADD COLUMN priority TEXT DEFAULT 'medium'",
        # chroma_status 추가: pending(적재 대기) / success(적재 완료) / failed(적재 실패)
        "ALTER TABLE documents ADD COLUMN chroma_status TEXT DEFAULT 'pending'",
    ]

    for sql in migrations:
        try:
            cursor.execute(sql)
            print(f"[migration] 적용: {sql}")
        except Exception:
            # 이미 존재하는 컬럼이면 무시
            pass

    conn.commit()
    conn.close()

    print("DB 초기화 완료:", settings.SQLITE_DB_PATH)


if __name__ == "__main__":
    init_db()