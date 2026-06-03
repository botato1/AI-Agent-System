from typing import List, Optional
from pydantic import BaseModel, Field

from backend.schemas.task_schema import TaskItemSchema


class NotionSaveRequest(BaseModel):
    id: Optional[str] = None
    title: str
    type: str
    source: str
    content: Optional[str] = None
    summary: Optional[str] = None
    language: Optional[str] = "ko"
    created_at: str
    tags: List[str] = Field(default_factory=list)
    status: str
    notion_url: Optional[str] = None
    chroma_id: Optional[str] = None
    user_edited: bool = False
    error: Optional[str] = None

    room_id: Optional[str] = None
    tasks: List[TaskItemSchema] = Field(default_factory=list)


class NotionSaveResponse(BaseModel):
    status: str
    notion_url: Optional[str] = None
    error: Optional[str] = None