# 채팅방/메시지 구조
from typing import List, Optional
from pydantic import BaseModel


# 대화 기록 안에 들어가는 메시지 하나의 최소 구조
class MessageSchema(BaseModel):
    message_id: Optional[str] = None  # 메시지 고유 UUID
    role: str                         # user / assistant / system
    content: str                      # 실제 메시지 내용
    created_at: Optional[str] = None  # 메시지 생성 시간

# React가 사용자의 채팅 메시지를 FastAPI로 보낼 때 사용하는 요청 구조
class ChatRequest(BaseModel):
    room_id: str            # 어느 채팅방에서 보낸 메시지인지
    content: str            # 사용자가 입력한 실제 질문
    source: str = "text"    # 입력 출처 text / voice / pdf / docx / md / image


# DB에 저장되거나 DB에서 조회되는 메시지의 구조
class ChatMessage(BaseModel):
    message_id: str     # 메시지 고유 UUID
    room_id: str        # 채팅방 ID
    role: str           # user / assistant / system
    content: str        # 메시지 내용
    created_at: str     # 메시지가 생성된 시간, ISO 8601


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