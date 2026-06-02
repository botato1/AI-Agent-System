# Notion 저장 요청 / 결과 구조
from typing import List, Optional
from pydantic import BaseModel

from schemas.task_schema import TaskItemSchema


# Notion에 저장할 데이터 구조
class NotionSaveRequest(BaseModel):
    id: Optional[str] = None
    title: str
    type: str
    source: str
    content: Optional[str] = None
    summary: Optional[str] = None
    tasks: List[TaskItemSchema] = []
    room_id: Optional[str] = None
    created_at: str
    notion_url: Optional[str] = None
    status: str
    error: Optional[str] = None


# Notion 저장 결과 구조
class NotionSaveResponse(BaseModel):
    status: str
    notion_url: Optional[str] = None
    error: Optional[str] = None