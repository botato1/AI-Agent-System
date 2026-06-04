import sqlite3
import uuid
from datetime import datetime, timezone
from backend.db.database import get_connection

def get_utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# ==========================================
# 1. conversations CRUD
# ==========================================

def create_conversation(title: str) -> str:
    conv_id = str(uuid.uuid4())
    now = get_utc_now()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO conversations (id, title, created_at, updated_at)
        VALUES (?, ?, ?, ?)
    """, (conv_id, title, now, now))
    conn.commit()
    conn.close()
    return conv_id

def update_conversation_timestamp(conversation_id: str):
    now = get_utc_now()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE conversations SET updated_at = ? WHERE id = ?
    """, (now, conversation_id))
    conn.commit()
    conn.close()

def get_conversations() -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, created_at, updated_at
        FROM conversations
        ORDER BY updated_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# ==========================================
# 2. messages CRUD
# ==========================================

def insert_message(conversation_id: str, role: str, content: str) -> str:
    msg_id = str(uuid.uuid4())
    now = get_utc_now()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO messages (id, conversation_id, role, content, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (msg_id, conversation_id, role, content, now))
    conn.commit()
    conn.close()
    update_conversation_timestamp(conversation_id)
    return msg_id

def get_messages(conversation_id: str) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT role, content, created_at FROM messages
        WHERE conversation_id = ?
        ORDER BY created_at ASC
    """, (conversation_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# ==========================================
# 3. summaries CRUD
# ==========================================

def insert_summary(conversation_id: str, summary_text: str, token_count: int = None):
    now = get_utc_now()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO summaries (conversation_id, summary, token_count, created_at)
        VALUES (?, ?, ?, ?)
    """, (conversation_id, summary_text, token_count, now))
    conn.commit()
    conn.close()

def get_latest_summary(conversation_id: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT summary, token_count, created_at FROM summaries
        WHERE conversation_id = ?
        ORDER BY created_at DESC LIMIT 1
    """, (conversation_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

# ==========================================
# 4. important_facts CRUD
# ==========================================

def insert_fact(conversation_id: str, fact_text: str, category: str = "환경"):
    now = get_utc_now()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO important_facts (conversation_id, fact, category, created_at)
        VALUES (?, ?, ?, ?)
    """, (conversation_id, fact_text, category, now))
    conn.commit()
    conn.close()

def get_all_facts(conversation_id: str) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT fact, category, created_at FROM important_facts
        WHERE conversation_id = ?
        ORDER BY created_at DESC
    """, (conversation_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# ==========================================
# 5. documents CRUD
# ==========================================

def save_document_metadata(doc: dict) -> str:
    """문서 처리 결과를 SQLite에 저장"""
    doc_id = doc.get("id", str(uuid.uuid4()))
    now = get_utc_now()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO documents
        (id, conversation_id, title, type, source, file_path, summary, status, notion_url, error, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        doc_id,
        doc.get("conversation_id", ""),
        doc.get("title", ""),
        doc.get("type", "document"),
        doc.get("source", ""),
        doc.get("file_path", ""),
        doc.get("summary", ""),
        doc.get("status", "processed"),
        doc.get("notion_url", ""),
        doc.get("error", ""),
        now
    ))
    conn.commit()
    conn.close()
    return doc_id

def get_documents(conversation_id: str) -> list:
    """채팅방 기준 문서 목록 조회"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, type, source, summary, status, created_at
        FROM documents
        WHERE conversation_id = ?
        ORDER BY created_at DESC
    """, (conversation_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# ==========================================
# 6. tasks CRUD
# ==========================================

def save_tasks(tasks: list, document_id: str, conversation_id: str):
    """액션아이템 목록 저장"""
    now = get_utc_now()
    conn = get_connection()
    cursor = conn.cursor()
    for task in tasks:
        task_id = task.get("task_id", str(uuid.uuid4()))
        cursor.execute("""
            INSERT INTO tasks
            (id, document_id, conversation_id, task, assignee, deadline, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task_id,
            document_id,
            conversation_id,
            task.get("task", ""),
            task.get("assignee", ""),
            task.get("deadline", ""),
            task.get("status", "todo"),
            now
        ))
    conn.commit()
    conn.close()

def get_tasks(conversation_id: str) -> list:
    """채팅방 기준 할일 목록 조회"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, task, assignee, deadline, status, created_at
        FROM tasks
        WHERE conversation_id = ?
        ORDER BY created_at DESC
    """, (conversation_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]