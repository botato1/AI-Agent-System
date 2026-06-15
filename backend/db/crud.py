import uuid
from datetime import datetime, timezone

from backend.db.database import get_connection


def get_utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# 첫 사용자 메시지를 기반으로 채팅방 제목을 자동 생성하는 함수
def make_conversation_title(content: str, max_length: int = 30) -> str:
    content = (content or "").strip().replace("\n", " ")

    if not content:
        return "새 채팅"

    if len(content) > max_length:
        return content[:max_length] + "..."

    return content


# ==========================================
# 1. conversations CRUD
# ==========================================

# 새 채팅방을 생성하는 함수
def create_conversation(title: str) -> str:
    conv_id = str(uuid.uuid4())
    now = get_utc_now()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO conversations (id, title, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        """,
        (conv_id, title, now, now),
    )

    conn.commit()
    conn.close()

    return conv_id


# 채팅방이 없으면 생성하고, 있으면 updated_at을 갱신하는 함수
def ensure_conversation(conversation_id: str, title: str = "새 채팅"):
    now = get_utc_now()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id
        FROM conversations
        WHERE id = ?
        """,
        (conversation_id,),
    )

    conversation = cursor.fetchone()

    if conversation is None:
        cursor.execute(
            """
            INSERT INTO conversations (id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (conversation_id, title, now, now),
        )
    else:
        cursor.execute(
            """
            UPDATE conversations
            SET updated_at = ?
            WHERE id = ?
            """,
            (now, conversation_id),
        )

    conn.commit()
    conn.close()


# 채팅방의 updated_at 값을 현재 시간으로 갱신하는 함수
def update_conversation_timestamp(conversation_id: str):
    now = get_utc_now()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE conversations
        SET updated_at = ?
        WHERE id = ?
        """,
        (now, conversation_id),
    )

    conn.commit()
    conn.close()


# 전체 채팅방 목록을 최신순으로 조회하는 함수
def get_conversations() -> list:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            c.id,
            c.title,
            c.created_at,
            c.updated_at,
            d.title AS filename
        FROM conversations c
        LEFT JOIN documents d
            ON d.id = (
                SELECT d2.id
                FROM documents d2
                WHERE d2.conversation_id = c.id
                ORDER BY d2.created_at DESC
                LIMIT 1
            )
        ORDER BY c.updated_at DESC
        """
    )

    rows = cursor.fetchall() or []
    conn.close()

    return [dict(row) for row in rows]


# 특정 채팅방 하나의 정보를 조회하는 함수
def get_conversation_by_id(room_id: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, title, created_at, updated_at
        FROM conversations
        WHERE id = ?
        """,
        (room_id,),
    )

    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)

    return None


# 채팅방과 해당 채팅방의 메시지를 삭제하는 함수
def delete_conversation(room_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM messages
        WHERE conversation_id = ?
        """,
        (room_id,),
    )

    cursor.execute(
        """
        DELETE FROM conversations
        WHERE id = ?
        """,
        (room_id,),
    )

    deleted_count = cursor.rowcount

    conn.commit()
    conn.close()

    return deleted_count > 0

# 모든 채팅방과 메시지를 삭제하는 함수
def delete_all_conversations_and_messages() -> dict:
    conn = get_connection()
    cursor = conn.cursor()

    # 메시지를 먼저 삭제
    cursor.execute("DELETE FROM messages")

    # 채팅방 삭제
    cursor.execute("DELETE FROM conversations")

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "message": "모든 채팅방과 메시지를 삭제했습니다."
    }

# ==========================================
# 2. messages CRUD
# ==========================================

# 메시지를 저장하고 채팅방이 없으면 자동으로 생성하는 함수
def insert_message(conversation_id: str, role: str, content: str) -> str:
    msg_id = str(uuid.uuid4())
    now = get_utc_now()

    conn = get_connection()
    cursor = conn.cursor()

    # 1. 채팅방이 이미 있는지 확인
    cursor.execute(
        """
        SELECT id
        FROM conversations
        WHERE id = ?
        """,
        (conversation_id,),
    )

    conversation = cursor.fetchone()

    # 2. 채팅방이 없으면 자동 생성
    if conversation is None:
        title = make_conversation_title(content) if role == "user" else "새 채팅"

        cursor.execute(
            """
            INSERT INTO conversations (id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (conversation_id, title, now, now),
        )

    # 3. 메시지 저장
    cursor.execute(
        """
        INSERT INTO messages (id, conversation_id, role, content, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (msg_id, conversation_id, role, content, now),
    )

    # 4. 채팅방 updated_at 갱신
    cursor.execute(
        """
        UPDATE conversations
        SET updated_at = ?
        WHERE id = ?
        """,
        (now, conversation_id),
    )

    conn.commit()
    conn.close()

    return msg_id


# 특정 채팅방의 메시지 목록을 시간순으로 조회하는 함수
def get_messages(conversation_id: str) -> list:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, role, content, created_at
        FROM messages
        WHERE conversation_id = ?
        ORDER BY created_at ASC
        """,
        (conversation_id,),
    )

    rows = cursor.fetchall() or []
    conn.close()

    return [dict(row) for row in rows]


# 특정 메시지 1개를 삭제하는 함수
def delete_message(message_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM messages
        WHERE id = ?
        """,
        (message_id,),
    )

    deleted_count = cursor.rowcount

    conn.commit()
    conn.close()

    return deleted_count > 0


# ==========================================
# 3. summaries CRUD
# ==========================================

# 특정 채팅방의 요약 내용을 저장하는 함수
def insert_summary(conversation_id: str, summary_text: str, token_count: int = None):
    now = get_utc_now()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO summaries (conversation_id, summary, token_count, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (conversation_id, summary_text, token_count, now),
    )

    conn.commit()
    conn.close()


# 특정 채팅방의 가장 최근 요약 내용을 조회하는 함수
def get_latest_summary(conversation_id: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT summary, token_count, created_at
        FROM summaries
        WHERE conversation_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (conversation_id,),
    )

    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)

    return None


# ==========================================
# 4. important_facts CRUD
# ==========================================

# 특정 채팅방의 중요 정보를 저장하는 함수
def insert_fact(conversation_id: str, fact_text: str, category: str = "환경"):
    now = get_utc_now()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO important_facts (conversation_id, fact, category, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (conversation_id, fact_text, category, now),
    )

    conn.commit()
    conn.close()


# 특정 채팅방의 중요 정보 목록을 조회하는 함수
def get_all_facts(conversation_id: str) -> list:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT fact, category, created_at
        FROM important_facts
        WHERE conversation_id = ?
        ORDER BY created_at DESC
        """,
        (conversation_id,),
    )

    rows = cursor.fetchall() or []
    conn.close()

    return [dict(row) for row in rows]


# ==========================================
# 5. documents CRUD
# ==========================================

# 문서 처리 결과를 SQLite에 저장하는 함수
def save_document_metadata(doc: dict) -> str:
    doc_id = doc.get("id", str(uuid.uuid4()))
    now = get_utc_now()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO documents
        (
            id,
            conversation_id,
            title,
            type,
            source,
            file_path,
            summary,
            status,
            notion_url,
            error,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
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
            now,
        ),
    )

    conn.commit()
    conn.close()

    return doc_id


# 채팅방 기준 문서 목록을 조회하는 함수
def get_documents(conversation_id: str) -> list:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, title, type, source, summary, status, created_at
        FROM documents
        WHERE conversation_id = ?
        ORDER BY created_at DESC
        """,
        (conversation_id,),
    )

    rows = cursor.fetchall() or []
    conn.close()

    return [dict(row) for row in rows]

# 전체 문서 목록을 조회하는 함수
def get_all_documents() -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id AS document_id,
            title AS filename,
            conversation_id AS room_id,
            created_at
        FROM documents
        ORDER BY created_at DESC
        """
    )

    rows = cursor.fetchall() or []
    conn.close()

    return [dict(row) for row in rows]

# ==========================================
# 6. tasks CRUD
# ==========================================

# 액션아이템 목록을 저장하는 함수
def save_tasks(tasks: list, document_id: str, conversation_id: str):
    now = get_utc_now()

    conn = get_connection()
    cursor = conn.cursor()

    for task in tasks:
        # LLM이 반환한 "0001", "0002" 같은 task_id는 중복될 수 있으므로
        # DB 저장용 id는 항상 UUID로 새로 생성한다.
        task_id = str(uuid.uuid4())

        cursor.execute(
            """
            INSERT INTO tasks
            (
                id,
                document_id,
                conversation_id,
                task,
                assignee,
                deadline,
                status,
                priority,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                document_id,
                conversation_id,
                task.get("task", ""),
                task.get("assignee", ""),
                task.get("deadline", ""),
                task.get("status", "todo"),
                task.get("priority", "medium"),
                now,
            ),
        )

    conn.commit()
    conn.close()


# 전체 업무 목록을 조회하는 함수
def get_all_tasks() -> list:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            document_id,
            conversation_id,
            task,
            assignee,
            deadline,
            status,
            priority,
            created_at
        FROM tasks
        ORDER BY created_at DESC
        """
    )

    rows = cursor.fetchall() or []
    conn.close()

    return [dict(row) for row in rows]


# 단일 task 생성 함수
def create_task(task_data: dict) -> dict:
    task_id = str(uuid.uuid4())
    now = get_utc_now()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO tasks
        (
            id,
            document_id,
            conversation_id,
            task,
            assignee,
            deadline,
            status,
            priority,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_id,
            task_data.get("document_id") or "",
            task_data.get("room_id") or task_data.get("conversation_id") or "",
            task_data.get("task", ""),
            task_data.get("assignee"),
            task_data.get("deadline"),
            task_data.get("status", "todo"),
            task_data.get("priority", "medium"),
            now,
        ),
    )

    conn.commit()
    conn.close()

    return {
        "task_id": task_id,
        "task": task_data.get("task", ""),
        "assignee": task_data.get("assignee"),
        "deadline": task_data.get("deadline"),
        "status": task_data.get("status", "todo"),
        "priority": task_data.get("priority", "medium"),
        "room_id": task_data.get("room_id") or task_data.get("conversation_id"),
        "document_id": task_data.get("document_id"),
        "created_at": now,
    }


# 특정 업무 상태를 변경하는 함수
def update_task_status(task_id: str, status: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE tasks
        SET status = ?
        WHERE id = ?
        """,
        (status, task_id),
    )

    updated_count = cursor.rowcount

    conn.commit()
    conn.close()

    return updated_count > 0


# 특정 업무 우선순위를 변경하는 함수
def update_task_priority(task_id: str, priority: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE tasks
        SET priority = ?
        WHERE id = ?
        """,
        (priority, task_id),
    )

    updated_count = cursor.rowcount

    conn.commit()
    conn.close()

    return updated_count > 0


# 특정 업무를 삭제하는 함수
def delete_task(task_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM tasks
        WHERE id = ?
        """,
        (task_id,),
    )

    deleted_count = cursor.rowcount

    conn.commit()
    conn.close()

    return deleted_count > 0


# 채팅방 기준 할 일 목록을 조회하는 함수
def get_tasks(conversation_id: str) -> list:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, task, assignee, deadline, status, priority, created_at
        FROM tasks
        WHERE conversation_id = ?
        ORDER BY created_at DESC
        """,
        (conversation_id,),
    )

    rows = cursor.fetchall() or []
    conn.close()

    return [dict(row) for row in rows]

def get_latest_document_by_conversation(conversation_id: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, title
        FROM documents
        WHERE conversation_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (conversation_id,),
    )

    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)

    return None

def get_document_by_filename_and_conversation(
    conversation_id: str,
    filename: str
) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, title
        FROM documents
        WHERE conversation_id = ?
          AND title = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (conversation_id, filename),
    )

    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)

    return None