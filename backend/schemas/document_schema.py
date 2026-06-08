# 문서 처리 결과 구조
from typing import List
from pydantic import BaseModel

from backend.schemas.common_schema import CommonDocumentSchema


# RAG 검색용 청크 하나의 구조
class ChunkSchema(BaseModel):
    chunk_id: str        # 청크 고유 ID
    page_number: int     # 원본 문서 페이지 번호
    content_type: str    # text / table / image / diagram
    content: str         # 청크 내용


# 문서 처리 관련 메타데이터
class DocumentMetadata(BaseModel):
    confidence_score: float   # OCR 또는 문서 추출 신뢰도
    engines: List[str]        # 사용된 문서 처리 엔진 목록
    fallback_used: bool       # fallback 사용 여부
    page_count: int           # 전체 페이지 수


# 최종 문서 처리 결과 구조
class DocumentResultSchema(CommonDocumentSchema):
    content_markdown: str
    chunks: List[ChunkSchema]
    metadata: DocumentMetadata