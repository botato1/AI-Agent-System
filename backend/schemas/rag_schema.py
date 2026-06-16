# ChromaDB / RAG 관련 구조
from typing import Optional, List
from pydantic import BaseModel, Field


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

    # 문서 검색/필터링용 메타데이터
    upload_context: Optional[str] = None   # "document"
    document_id: Optional[str] = None      # 문서 하나의 고유 ID
    filename: Optional[str] = None         # 원본 파일명
    chunk_index: Optional[int] = None      # 몇 번째 chunk인지
    room_id: Optional[str] = None          # 현재는 사용 안 해도 됨

    notion_url: Optional[str] = None
    error: Optional[str] = None
    chunk_id: Optional[str] = None
    page_number: Optional[int] = None
    content_type: Optional[str] = None

class RagSearchItemSchema(BaseModel):
    id: str
    content: str
    source: str
    source_url: Optional[str] = None
    data_type: Optional[str] = None
    importance: Optional[int] = None
    score: Optional[float] = None
    title: Optional[str] = None
    created_at: Optional[str] = None


class RagSearchResponseSchema(BaseModel):
    status: str
    query: str
    count: int
    data: List[RagSearchItemSchema] = Field(default_factory=list)
    error: Optional[str] = None


class ChromaSearchResultSchema(BaseModel):
    id: str
    content: str
    metadata: ChromaMetadataSchema
    score: Optional[float] = None



# Ollama 요청 구조
class OllamaRequest(BaseModel):
    user_input: str
    conversation_id: Optional[str] = None
    filter_type: Optional[str] = None


# Ollama 응답 구조
class OllamaResponse(BaseModel):
    status: str
    original_input: str
    normalized_input: str
    intent: str
    answer: str
    sources: List[str] = Field(default_factory=list)
    error: Optional[str] = None