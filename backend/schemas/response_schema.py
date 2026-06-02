# FastAPI 최종 응답 구조
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from schemas.task_schema import TaskItemSchema


# RAG 검색에 사용된 참고 문서 정보
class SourceSchema(BaseModel):
    id: str
    title: str
    source: str
    score: Optional[float] = None
    created_at: Optional[str] = None
    notion_url: Optional[str] = None
    tags: Optional[List[str]] = None


# Notion 저장 결과
class NotionResultSchema(BaseModel):
    status: str
    notion_url: Optional[str] = None
    error: Optional[str] = None


# React에 반환할 최종 채팅 응답 구조
class ChatResponseSchema(BaseModel):
    room_id: str
    answer: str
    summary: Optional[str] = None
    tasks: List[TaskItemSchema] = []
    sources: List[SourceSchema] = []
    notion_result: Optional[NotionResultSchema] = None
    graph_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None