# 채팅 관련 API 엔드포인트
from fastapi import APIRouter

from backend.schemas.chat_schema import ChatRequest, ChatHistoryResponse
from backend.schemas.response_schema import ChatResponseSchema
from backend.db.crud import insert_message, get_messages


router = APIRouter(
    prefix="/api",
    tags=["Chat"]
)


# 사용자 채팅 메시지 전송 API
@router.post("/chat", response_model=ChatResponseSchema)
def send_chat_message(request: ChatRequest):

    # 1. 사용자 메시지 DB 저장
    insert_message(
        conversation_id=request.room_id,
        role="user",
        content=request.content
    )

    # 2. 임시 assistant 응답 생성 (LangGraph 연결 전 더미 데이터)
    answer = "현재는 LangGraph 연결 전 더미 응답입니다."

    # 3. assistant 메시지 DB 저장
    insert_message(
        conversation_id=request.room_id,
        role="assistant",
        content=answer
    )

    # 4. 프론트로 응답 반환
    return {
        "room_id": request.room_id,
        "answer": answer,
        "summary": None,
        "tasks": [],
        "sources": [],
        "notion_result": None,
        "graph_data": None,
        "error": None
    }


# 특정 채팅방의 이전 대화 기록 조회 API
@router.get("/conversations/{room_id}/messages", response_model=ChatHistoryResponse)
def get_chat_history(room_id: str):

    rows = get_messages(room_id)

    messages = [
        {
            "role": row[0],
            "content": row[1],
            "created_at": row[2]
        }
        for row in rows
    ]

    return {
        "room_id": room_id,
        "messages": messages
    }