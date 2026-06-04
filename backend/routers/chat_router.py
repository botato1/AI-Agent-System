# 채팅 관련 API 엔드포인트
from fastapi import APIRouter

from backend.schemas.chat_schema import ChatRequest, ChatHistoryResponse
from backend.schemas.response_schema import ChatResponseSchema


router = APIRouter(
    prefix="/api",
    tags=["Chat"]
)


# 사용자 채팅 메시지 전송 API
# 현재는 LangGraph 전체 연결 전이므로 더미 응답을 반환
@router.post("/chat", response_model=ChatResponseSchema)
def send_chat_message(request: ChatRequest):

    return {
        "room_id": request.room_id,
        "answer": "현재는 LangGraph 연결 전 더미 응답입니다.",
        "summary": None,
        "tasks": [],
        "sources": [],
        "notion_result": None,
        "graph_data": None,
        "error": None
    }


# 특정 채팅방의 이전 대화 기록 조회 API
# 현재는 DB 연결 전이므로 빈 messages 배열을 반환
@router.get("/conversations/{room_id}/messages", response_model=ChatHistoryResponse)
def get_chat_history(room_id: str):

    return {
        "room_id": room_id,
        "messages": []
    }