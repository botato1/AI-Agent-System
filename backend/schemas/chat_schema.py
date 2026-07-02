from typing import List, Optional
from pydantic import BaseModel


# 대화 기록 안에 들어가는 메시지 하나의 최소 구조
class MessageSchema(BaseModel):
    message_id: Optional[str] = None
    role: str
    content: str
    created_at: Optional[str] = None


# React가 사용자의 채팅 메시지를 FastAPI로 보낼 때 사용하는 요청 구조
class ChatRequest(BaseModel):
    room_id: str
    content: str
    source: str = "text"

    # 프론트에서 선택한 문서 식별값
    target_document_id: Optional[str] = None
    target_filename: Optional[str] = None
    target_document_ids: Optional[List[str]] = None


# DB에 저장되거나 DB에서 조회되는 메시지의 구조
class ChatMessage(BaseModel):
    message_id: str
    room_id: str
    role: str
    content: str
    created_at: str


# 이전 대화 기록을 React 또는 LangGraph에 반환할 때 쓰는 구조
class ChatHistoryResponse(BaseModel):
    room_id: str
    messages: List[MessageSchema]


# 채팅방 세션 구조
class ConversationSchema(BaseModel):
    room_id: str
    title: str
    created_at: str
    updated_at: str


# 채팅방 목록 응답 구조
class ConversationListResponse(BaseModel):
    conversations: List[ConversationSchema]