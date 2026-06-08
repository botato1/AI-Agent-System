# 공통 키 14개 정의
from typing import Optional, List
# pydantic : Python에서 데이터 검증 및 설정 관리를 위한 라이브러리
from pydantic import BaseModel

class CommonDocumentSchema(BaseModel):
    id: str                         # 문서 / STT / 파일 결과 고유 UUID
    title: str                      # 문서 제목 또는 원본 파일명
    type: str                       # meeting / memo / document / image / voice
    source: str                     # voice / text / pdf / docx / md / image
    content: str                    # 원본 텍스트, 항상 string
    summary: Optional[str] = None   # AI 요약본
    language: str                   # ko / en
    created_at: str                 # ISO 8601 형식 생성/처리 시각
    tags: List[str]                 # 태그 배열
    status: str                     # uploaded / processing / processed / error
    notion_url: Optional[str] = None
    chroma_id: Optional[str] = None
    error: Optional[str] = None

    user_edited : bool = False  # 사용자가 STT/문서 처리 결과를 직접 수정했는지 여부