# Notion 저장 관련 API 엔드포인트
from fastapi import APIRouter

from backend.schemas.notion_schema import NotionSaveRequest, NotionSaveResponse
from backend.services.notion_service import save_to_notion


router = APIRouter(
    prefix="/api/notion",
    tags=["Notion"]
)


# 요약, 원본 내용, 할 일 목록을 Notion 데이터베이스에 저장하는 API
@router.post("/save", response_model=NotionSaveResponse)
def save_notion_page(request: NotionSaveRequest):


    result = save_to_notion(request)

    return result