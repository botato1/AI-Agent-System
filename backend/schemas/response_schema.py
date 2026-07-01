from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from backend.schemas.task_schema import TaskItemSchema


class SourceSchema(BaseModel):
    id: str
    title: Optional[str] = None
    source: str
    source_url: Optional[str] = None
    data_type: Optional[str] = None
    score: Optional[float] = None
    importance: Optional[int] = None
    created_at: Optional[str] = None
    tags: Optional[List[str]] = None



class ChatResponseSchema(BaseModel):
    room_id: str
    answer: str
    summary: Optional[str] = None
    tasks: List[TaskItemSchema] = Field(default_factory=list)
    sources: List[SourceSchema] = Field(default_factory=list)
    graph_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None