# backend/db/crud.py
import uuid
from datetime import datetime, timezone

from backend.db.database import get_connection


def get_utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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

def create_conversation(title: str) -> str:
    conv_id = str(uuid.uuid4())
    now = get_utc_now()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO conversations (
            id,
            title,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (conv_id, title, now, now),
    )
    conn.commit()
    conn.close()

    return conv_id


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

    if cursor.fetchone() is None:
        cursor.execute(
            """
            INSERT INTO conversations (
                id,
                title,
                created_at,
                updated_at
            )
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


def get_conversations() -> list:
    """
    전체 채팅방 목록을 최신순으로 조회한다.
    각 채팅방의 최근 문서 제목도 함께 조회한다.
    """
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

    return dict(row) if row else None


def delete_conversation(room_id: str) -> bool:
    """
    채팅방과 연관된 모든 데이터를 삭제한다.
    document_chunks는 documents를 기준으로 연결되어 있으므로 documents 삭제 전에 먼저 삭제한다.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM document_chunks
        WHERE document_id IN (
            SELECT id
            FROM documents
            WHERE conversation_id = ?
        )
        """,
        (room_id,),
    )
    cursor.execute(
        """
        DELETE FROM messages
        WHERE conversation_id = ?
        """,
        (room_id,),
    )
    cursor.execute(
        """
        DELETE FROM tasks
        WHERE conversation_id = ?
        """,
        (room_id,),
    )
    cursor.execute(
        """
        DELETE FROM documents
        WHERE conversation_id = ?
        """,
        (room_id,),
    )
    cursor.execute(
        """
        DELETE FROM summaries
        WHERE conversation_id = ?
        """,
        (room_id,),
    )
    cursor.execute(
        """
        DELETE FROM important_facts
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


def delete_all_conversations_and_messages() -> dict:
    """
    전체 채팅방 및 연관 데이터를 전부 삭제한다.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM document_chunks")
    cursor.execute("DELETE FROM tasks")
    cursor.execute("DELETE FROM messages")
    cursor.execute("DELETE FROM summaries")
    cursor.execute("DELETE FROM important_facts")
    cursor.execute("DELETE FROM documents")
    cursor.execute("DELETE FROM conversations")

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "message": "모든 채팅방과 메시지를 삭제했습니다.",
    }


# ==========================================
# 2. messages CRUD
# ==========================================

def insert_message(conversation_id: str, role: str, content: str) -> str:
    msg_id = str(uuid.uuid4())
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

    if cursor.fetchone() is None:
        title = make_conversation_title(content) if role == "user" else "새 채팅"
        cursor.execute(
            """
            INSERT INTO conversations (
                id,
                title,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (conversation_id, title, now, now),
        )

    cursor.execute(
        """
        INSERT INTO messages (
            id,
            conversation_id,
            role,
            content,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (msg_id, conversation_id, role, content, now),
    )
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
# memory_node에서 대화 요약 저장/조회 시 사용
# ==========================================

def insert_summary(conversation_id: str, summary_text: str, token_count: int = None):
    now = get_utc_now()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO summaries (
            conversation_id,
            summary,
            token_count,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (conversation_id, summary_text, token_count, now),
    )
    conn.commit()
    conn.close()


def get_latest_summary(conversation_id: str) -> dict | None:
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

    return dict(row) if row else None


# ==========================================
# 4. important_facts CRUD
# memory_node에서 중요 정보 저장/조회 시 사용
# ==========================================

def insert_fact(conversation_id: str, fact_text: str, category: str = "환경"):
    now = get_utc_now()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO important_facts (
            conversation_id,
            fact,
            category,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (conversation_id, fact_text, category, now),
    )
    conn.commit()
    conn.close()


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

def save_document_metadata(doc: dict) -> str:
    """
    문서/STT 결과 메타데이터를 documents 테이블에 저장한다.

    metadata는 STT 상세 조회에서 duration_sec, model_used, original_file_url 등을
    복원하기 위해 JSON 문자열 형태로 저장한다.
    """
    doc_id = doc.get("id") or str(uuid.uuid4())
    now = get_utc_now()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO documents (
            id,
            conversation_id,
            title,
            type,
            source,
            file_path,
            json_path,
            content_markdown,
            summary,
            status,
            notion_url,
            error,
            metadata,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            conversation_id = excluded.conversation_id,
            title = excluded.title,
            type = excluded.type,
            source = excluded.source,
            file_path = excluded.file_path,
            json_path = excluded.json_path,
            content_markdown = excluded.content_markdown,
            summary = excluded.summary,
            status = excluded.status,
            notion_url = excluded.notion_url,
            error = excluded.error,
            metadata = excluded.metadata,
            created_at = excluded.created_at
        """,
        (
            doc_id,
            doc.get("conversation_id", ""),
            doc.get("title", ""),
            doc.get("type", "document"),
            doc.get("source", ""),
            doc.get("file_path", ""),
            doc.get("json_path", ""),
            doc.get("content_markdown", ""),
            doc.get("summary", ""),
            doc.get("status", "processed"),
            doc.get("notion_url", ""),
            doc.get("error", ""),
            doc.get("metadata", "{}"),
            now,
        ),
    )
    conn.commit()
    conn.close()

    return doc_id


def get_documents(conversation_id: str) -> list:
    """
    특정 채팅방의 문서 목록을 조회한다.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            id,
            title,
            type,
            source,
            summary,
            status,
            chroma_status,
            created_at,
            json_path,
            metadata
        FROM documents
        WHERE conversation_id = ?
        ORDER BY created_at DESC
        """,
        (conversation_id,),
    )
    rows = cursor.fetchall() or []
    conn.close()

    return [dict(row) for row in rows]


def get_document_by_id(document_id: str) -> dict | None:
    """
    document_id 기준으로 문서 단건을 조회한다.
    STT 상세 조회에서도 사용한다.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            id,
            conversation_id,
            title,
            type,
            source,
            file_path,
            json_path,
            content_markdown,
            summary,
            status,
            chroma_status,
            notion_url,
            error,
            metadata,
            created_at
        FROM documents
        WHERE id = ?
        LIMIT 1
        """,
        (document_id,),
    )
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def get_all_documents() -> list:
    """
    전체 문서 목록 조회.
    voice 타입은 제외하고 document/meeting 타입만 반환한다.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            id              AS document_id,
            title           AS filename,
            conversation_id AS room_id,
            type,
            json_path,
            chroma_status,
            metadata,
            created_at
        FROM documents
        WHERE type != 'voice'
        ORDER BY created_at DESC
        """
    )
    rows = cursor.fetchall() or []
    conn.close()

    return [dict(row) for row in rows]


def get_latest_document_by_conversation(conversation_id: str) -> dict | None:
    """
    특정 채팅방의 가장 최근 업로드 문서를 조회한다.
    chat_service에서 target_document_id 보완할 때 사용한다.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, title, json_path, metadata
        FROM documents
        WHERE conversation_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (conversation_id,),
    )
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def get_document_by_filename_and_conversation(
    conversation_id: str,
    filename: str,
) -> dict | None:
    """
    특정 채팅방에서 파일명으로 문서를 조회한다.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, title, json_path, metadata
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

    return dict(row) if row else None


def _get_voice_documents(conversation_id: str | None = None) -> list[dict]:
    """
    음성 문서 목록 조회 공통 함수.

    conversation_id가 있으면 특정 채팅방의 음성 목록을 조회하고,
    없으면 전체 업로드 음성 목록을 조회한다.
    """
    conn = get_connection()
    cursor = conn.cursor()

    if conversation_id:
        cursor.execute(
            """
            SELECT
                id,
                conversation_id,
                title,
                type,
                source,
                file_path,
                summary,
                status,
                chroma_status,
                metadata,
                created_at
            FROM documents
            WHERE conversation_id = ?
              AND type = 'voice'
            ORDER BY created_at DESC
            """,
            (conversation_id,),
        )
    else:
        cursor.execute(
            """
            SELECT
                id,
                conversation_id,
                title,
                type,
                source,
                file_path,
                summary,
                status,
                chroma_status,
                metadata,
                created_at
            FROM documents
            WHERE type = 'voice'
            ORDER BY created_at DESC
            """
        )

    rows = cursor.fetchall() or []
    conn.close()

    return [dict(row) for row in rows]


def get_all_voice_documents() -> list[dict]:
    """
    업로드된 모든 음성 문서 목록을 조회한다.
    프론트 음성 목록 페이지에서 사용한다.
    """
    return _get_voice_documents()


def get_voice_documents_by_conversation(conversation_id: str) -> list[dict]:
    """
    특정 채팅방에 업로드된 음성 문서 목록을 조회한다.
    필요 시 채팅방별 필터링에 사용한다.
    """
    return _get_voice_documents(conversation_id=conversation_id)


def delete_document(document_id: str) -> bool:
    """
    documents 테이블에서 특정 문서 하나를 삭제한다.
    document_chunks 삭제는 호출부에서 먼저 처리하는 것을 권장한다.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        DELETE FROM documents
        WHERE id = ?
        """,
        (document_id,),
    )
    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    return deleted > 0


# ==========================================
# 6. tasks CRUD
# ==========================================

def save_tasks(tasks: list, document_id: str, conversation_id: str):
    now = get_utc_now()

    conn = get_connection()
    cursor = conn.cursor()

    for task in tasks:
        task_id = str(uuid.uuid4())
        cursor.execute(
            """
            INSERT INTO tasks (
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


def create_task(task_data: dict) -> dict:
    task_id = str(uuid.uuid4())
    now = get_utc_now()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO tasks (
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


def get_tasks_by_document(document_id: str) -> list:
    """
    특정 문서에서 추출된 task 목록을 조회한다.
    문서 상세 조회 API에서 사용한다.
    """
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
        WHERE document_id = ?
        ORDER BY created_at DESC
        """,
        (document_id,),
    )
    rows = cursor.fetchall() or []
    conn.close()

    return [dict(row) for row in rows]


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
    updated = cursor.rowcount
    conn.commit()
    conn.close()

    return updated > 0


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
    updated = cursor.rowcount
    conn.commit()
    conn.close()

    return updated > 0


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
    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    return deleted > 0


# ==========================================
# 7. document_chunks CRUD
# STT 발화(transcription) 단위 저장/조회.
# ChromaDB 검색용 chunk와는 별개.
# 화면 표시/사용자 수정용.
# ==========================================

def save_document_chunks(document_id: str, transcription: list[dict]) -> int:
    """
    STT transcription 결과를 document_chunks 테이블에 저장한다.
    """
    if not document_id or not transcription:
        return 0

    conn = get_connection()
    cursor = conn.cursor()
    saved_count = 0

    for idx, seg in enumerate(transcription):
        content = seg.get("text") or ""
        if not content.strip():
            continue

        cursor.execute(
            """
            INSERT INTO document_chunks (
                document_id,
                chunk_index,
                content,
                start_time,
                end_time,
                speaker,
                content_type,
                user_edited
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                idx,
                content.strip(),
                seg.get("start"),
                seg.get("end"),
                seg.get("speaker"),
                seg.get("content_type", "transcription"),
                1 if seg.get("user_edited") else 0,
            ),
        )
        saved_count += 1

    conn.commit()
    conn.close()

    return saved_count


def get_document_chunks(document_id: str) -> list:
    """
    특정 문서의 chunk 전체를 순서대로 조회한다.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            id,
            document_id,
            chunk_index,
            content,
            start_time,
            end_time,
            speaker,
            content_type,
            user_edited,
            created_at
        FROM document_chunks
        WHERE document_id = ?
        ORDER BY chunk_index ASC
        """,
        (document_id,),
    )
    rows = cursor.fetchall() or []
    conn.close()

    return [dict(row) for row in rows]


def update_chunk_content(chunk_id: int, new_content: str) -> bool:
    """
    사용자가 발화 내용을 수정했을 때 content를 갱신하고,
    user_edited를 1로 표시한다.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE document_chunks
        SET content = ?,
            user_edited = 1
        WHERE id = ?
        """,
        (new_content, chunk_id),
    )
    updated = cursor.rowcount
    conn.commit()
    conn.close()

    return updated > 0


def delete_document_chunks(document_id: str) -> int:
    """
    특정 문서의 chunk 전체를 삭제한다.
    STT 재처리 또는 재적재 시 중복 저장을 방지하기 위해 사용한다.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        DELETE FROM document_chunks
        WHERE document_id = ?
        """,
        (document_id,),
    )
    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    return deleted


def update_chroma_status(document_id: str, status: str) -> bool:
    """
    documents 테이블의 chroma_status를 업데이트한다.
    status: "pending" / "success" / "failed"
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE documents SET chroma_status = ? WHERE id = ?",
        (status, document_id),
    )
    updated = cursor.rowcount
    conn.commit()
    conn.close()
    return updated > 0


def get_documents_by_chroma_status(status: str) -> list:
    """
    chroma_status 기준으로 문서 목록 조회.
    재시도 대상 조회: get_documents_by_chroma_status("failed")
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, conversation_id, title, type, source, json_path, chroma_status, created_at
        FROM documents WHERE chroma_status = ? ORDER BY created_at DESC
        """,
        (status,),
    )
    rows = cursor.fetchall() or []
    conn.close()
    return [dict(row) for row in rows]