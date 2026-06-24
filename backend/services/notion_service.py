from typing import List

from backend.modules.notion.notion_client import get_notion_client
from backend.core.config import settings
from backend.schemas.notion_schema import NotionSaveRequest, NotionSaveResponse
from backend.schemas.task_schema import TaskItemSchema


# Notion 일반 문단 블록 생성
def _plain_text_block(text: str):
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        }
    }


# Notion 제목(heading_2) 블록 생성
def _heading_block(text: str):
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        }
    }


# TaskItemSchema를 Notion 저장용 문자열로 변환
def _task_to_text(task: TaskItemSchema) -> str:
    return (
        f"- 업무: {task.task}\n"
        f"  담당자: {task.assignee or '미정'}\n"
        f"  마감일: {task.deadline or '미정'}\n"
        f"  상태: {task.status}"
    )


# Notion 페이지 본문 블록 목록 생성 (요약 → 원본 내용 → 할 일 순서)
def _make_notion_children(request: NotionSaveRequest) -> List[dict]:
    children = []

    if request.summary:
        children.append(_heading_block("요약"))
        children.append(_plain_text_block(request.summary))

    if request.content:
        children.append(_heading_block("원본 내용"))
        children.append(_plain_text_block(request.content[:1800]))

    if request.tasks:
        children.append(_heading_block("추출된 할 일"))
        for task in request.tasks:
            children.append(_plain_text_block(_task_to_text(task)))

    if not children:
        children.append(_plain_text_block("저장할 내용이 없습니다."))

    return children


# Notion DB에서 title 타입 속성 이름을 동적으로 찾아 반환 (속성명 변경 대응)
def _get_title_property_name() -> str:
    notion = get_notion_client()
    database = notion.databases.retrieve(database_id=settings.NOTION_DATABASE_ID)
    properties = database.get("properties", {})

    for name, info in properties.items():
        if info.get("type") == "title":
            return name

    return "회의록 제목"


# 요약, 할 일, 문서 내용을 Notion 데이터베이스에 저장
def save_to_notion(request: NotionSaveRequest) -> NotionSaveResponse:
    try:
        if not settings.NOTION_DATABASE_ID:
            return NotionSaveResponse(
                status="error",
                notion_url=None,
                error="NOTION_DATABASE_ID가 설정되지 않았습니다."
            )

        notion = get_notion_client()
        title_property_name = _get_title_property_name()

        page = notion.pages.create(
            parent={"database_id": settings.NOTION_DATABASE_ID},
            properties={
                title_property_name: {
                    "title": [{"text": {"content": request.title}}]
                },
                "요약": {
                    "rich_text": [{"text": {"content": request.summary or ""}}]
                },
                "작성일": {
                    "date": {"start": request.created_at}
                },
                "상태": {
                    "select": {"name": request.status}
                }
            },
            children=_make_notion_children(request)
        )

        return NotionSaveResponse(status="success", notion_url=page.get("url"), error=None)

    except Exception as e:
        return NotionSaveResponse(status="error", notion_url=None, error=str(e))