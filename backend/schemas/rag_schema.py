# ChromaDB / RAG 관련 구조
from typing import Optional, List
from pydantic import BaseModel


class ChromaMetadataSchema(BaseModel):
    id: str
    title: str
    type: str
    source: str
    language: str
    created_at: str
    status: str
    chroma_id: str
    user_edited: bool
    tags: str                   # ChromaDB에는 콤마 문자열로 저장
    importance_score: int

    notion_url: Optional[str] = None
    error: Optional[str] = None
    chunk_id: Optional[str] = None
    page_number: Optional[int] = None
    content_type: Optional[str] = None


class ChromaSearchResultSchema(BaseModel):
    id: str
    content: str
    metadata: ChromaMetadataSchema
    score: Optional[float] = None


class RagSearchResponseSchema(BaseModel):
    results: List[ChromaSearchResultSchema]