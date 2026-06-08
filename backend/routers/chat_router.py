# 채팅 관련 API 엔드포인트
from fastapi import APIRouter
from pydantic import BaseModel

from backend.schemas.chat_schema import ChatRequest, ChatHistoryResponse
from backend.schemas.response_schema import ChatResponseSchema
from backend.services.chat_service import handle_chat
from backend.db.crud import create_conversation, get_conversations, get_messages, delete_conversation, delete_message, get_conversation_by_id

class ConversationCreateRequest(BaseModel):
    title : str = "새 대화"

router = APIRouter(
    prefix="/api",
    tags=["Chat"]
)


# 사용자 채팅 메시지 전송 API
@router.post("/chat", response_model=ChatResponseSchema)
async def send_chat_message(request: ChatRequest):
    return await handle_chat(request)


# 특정 채팅방의 이전 대화 기록 조회 API
@router.get("/conversations/{room_id}/messages", response_model=ChatHistoryResponse)
def get_chat_history(room_id: str):

    rows = get_messages(room_id)

    messages = [
        {
            "message_id": row[0],
            "role": row[1],
            "content": row[2],
            "created_at": row[3]
        }
        for row in rows
    ]

    return {
        "room_id": room_id,
        "messages": messages
    }

# 새 채팅방을 생성하는 API
@router.post("/conversations")
def create_chat_room(request: ConversationCreateRequest):
    room_id = create_conversation(request.title)

    return {
        "room_id" : room_id,
        "title" : request.title
    }

# 전체 채팅방 목록을 조회하는 API
@router.get("/conversations")
def get_chat_rooms():
    rows = get_conversations()

    conversations = [
        {
            "room_id": row[0],
            "title": row[1],
            "created_at": row[2],
            "updated_at": row[3]
        }
        for row in rows
    ]

    return {
        "conversations": conversations
    }

# 채팅방 단건 조회 API
@router.get("/conversations/{room_id}")
def get_conversation_detail(room_id: str):
    row = get_conversation_by_id(room_id)

    if not row:
        return {
            "status": "error",
            "room_id": room_id,
            "message": "채팅방을 찾을 수 없습니다",
            "error": "conversation_not_found"
        }
    
    return {
        "status": "success",
        "room_id": row[0],
        "title": row[1],
        "created_at": row[2],
        "updated_at": row[3],
        "error": None
    }

# 채팅방 삭제 API : 특정 채팅방과 해당 채팅방의 메시지를 삭제하는 몌ㅑ
@router.delete("/conversations/{room_id}")
def remove_chat_room(room_id: str):
    deleted = delete_conversation(room_id)

    if not deleted:
        return {
            "status": "error",
            "room_id": room_id,
            "message": "삭제할 채팅방을 찾을 수 없습니다.",
            "error": "conversation_not_found"
        }

    return {
        "status": "success",
        "room_id": room_id,
        "message": "채팅방이 삭제되었습니다.",
        "error": None
    }

# 메시지 삭제 API : 특정 메시지 1개를 삭제하는 API
@router.delete("/messages/{message_id}")
def remove_message(message_id: str):
    deleted = delete_message(message_id)

    if not deleted:
        return {
            "status": "error",
            "message_id": message_id,
            "message": "삭제할 메시지를 찾을 수 없습니다.",
            "error": "message_not_found"
        }

    return {
        "status": "success",
        "message_id": message_id,
        "message": "메시지가 삭제되었습니다.",
        "error": None
    }