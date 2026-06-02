import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "storage" / "sqlite" / "chat.db"


def get_conn():
    return sqlite3.connect(DB_PATH)


# 1. 채팅방 생성
def create_conversation(title: str):
    conn = get_conn()
    cursor = conn.cursor()

    conv_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    cursor.execute("""
    INSERT INTO conversations (id, title, created_at, updated_at)
    VALUES (?, ?, ?, ?)
    """, (conv_id, title, now, now))

    conn.commit()
    conn.close()

    return conv_id


# 2. 메시지 저장
def insert_message(conversation_id: str, role: str, content: str):
    conn = get_conn()
    cursor = conn.cursor()

    msg_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    cursor.execute("""
    INSERT INTO messages (id, conversation_id, role, content, created_at)
    VALUES (?, ?, ?, ?, ?)
    """, (msg_id, conversation_id, role, content, now))

    conn.commit()
    conn.close()

    return msg_id


# 3. 메시지 가져오기
def get_messages(conversation_id: str):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT role, content, created_at
    FROM messages
    WHERE conversation_id = ?
    ORDER BY created_at ASC
    """, (conversation_id,))

    rows = cursor.fetchall()
    conn.close()

    return rows


# 4. 채팅방 업데이트 시간 갱신
def update_conversation_time(conversation_id: str):
    conn = get_conn()
    cursor = conn.cursor()

    now = datetime.utcnow().isoformat()

    cursor.execute("""
    UPDATE conversations
    SET updated_at = ?
    WHERE id = ?
    """, (now, conversation_id))

    conn.commit()
    conn.close()

#5. 이후 추가 