import sqlite3
import uuid
from datetime import datetime, timezone
from backend.db.database import DB_PATH  # database.py에 정의된 DB_PATH를 그대로 가져옵니다.


def get_utc_now() -> str:
    """ISO 8601 UTC 포맷의 현재 시각 반환 (예: 2026-06-02T16:58:50Z)"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ==========================================
# 1. conversations (채팅방 세션) CRUD
# ==========================================

def create_conversation(title: str) -> str:
    """채팅방 처음 생성될 때 INSERT 후 생성된 ID 반환"""
    conv_id = str(uuid.uuid4())
    now = get_utc_now()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO conversations (id, title, created_at, updated_at)
        VALUES (?, ?, ?, ?)
    """, (conv_id, title, now, now))
    conn.commit()
    conn.close()
    return conv_id


def update_conversation_timestamp(conversation_id: str):
    """메시지가 올 때마다 updated_at을 현재 시간으로 UPDATE"""
    now = get_utc_now()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE conversations SET updated_at = ? WHERE id = ?
    """, (now, conversation_id))
    conn.commit()
    conn.close()


# ==========================================
# 2. messages (전체 채팅 메시지 로그) CRUD
# ==========================================

def insert_message(conversation_id: str, role: str, content: str) -> str:
    """메시지 전송/수신마다 INSERT + 대화방 Last Update 최신화"""
    msg_id = str(uuid.uuid4())
    now = get_utc_now()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO messages (id, conversation_id, role, content, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (msg_id, conversation_id, role, content, now))
    conn.commit()
    conn.close()
    
    # 메시지 추가 시 세션 시간 자동 업데이트
    update_conversation_timestamp(conversation_id)
    return msg_id


def get_messages(conversation_id: str) -> list:
    """LangGraph 컨텍스트 전달 및 화면 렌더링용 SELECT ORDER BY created_at ASC"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT role, content, created_at FROM messages 
        WHERE conversation_id = ? 
        ORDER BY created_at ASC
    """, (conversation_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


# ==========================================
# 3. summaries (채팅방별 컨텍스트 요약본) CRUD
# ==========================================

def insert_summary(conversation_id: str, summary_text: str, token_count: int = None):
    """메시지가 일정 토큰 초과 시 자동 요약본 INSERT"""
    now = get_utc_now()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO summaries (conversation_id, summary, token_count, created_at)
        VALUES (?, ?, ?, ?)
    """, (conversation_id, summary_text, token_count, now))
    conn.commit()
    conn.close()


def get_latest_summary(conversation_id: str) -> dict:
    """최신 요약 1건 SELECT (없으면 None)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT summary, token_count, created_at FROM summaries 
        WHERE conversation_id = ? 
        ORDER BY created_at DESC LIMIT 1
    """, (conversation_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {"summary": row[0], "token_count": row[1], "created_at": row[2]}
    return None


# ==========================================
# 4. important_facts (유저 개인화 정보 저장고) CRUD
# ==========================================

def insert_fact(conversation_id: str, fact_text: str, category: str = "환경"):
    """Agent가 대화 중 개인화 정보 감지 시 INSERT (동현 님 need_memory 트리거 연동)"""
    now = get_utc_now()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO important_facts (conversation_id, fact, category, created_at)
        VALUES (?, ?, ?, ?)
    """, (conversation_id, fact_text, category, now))
    conn.commit()
    conn.close()


def get_all_facts(conversation_id: str) -> list:
    """새 대화 시작 시 과거 맥락 로드 및 개인화 응답 생성용 SELECT (최신순)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT fact, category, created_at FROM important_facts 
        WHERE conversation_id = ? 
        ORDER BY created_at DESC
    """, (conversation_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows