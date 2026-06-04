# Notion 저장
from typing import List

from backend.modules.notion.notion_client import get_notion_client
from backend.core.config import settings
from backend.schemas.notion_schema import NotionSaveRequest, NotionSaveResponse
from backend.schemas.task_schema import TaskItemSchema


def _plain_text_block(text: str):
    """
    Notion에 일반 문단 블록을 만들기 위한 함수
    """
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {
                        "content": text
                    }
                }
            ]
        }
    }


def _heading_block(text: str):
    """
    Notion에 제목 블록을 만들기 위한 함수
    """
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {
                        "content": text
                    }
                }
            ]
        }
    }


def _task_to_text(task: TaskItemSchema) -> str:
    """
    TaskItemSchema 하나를 Notion에 넣기 좋은 문자열로 변환
    """
    assignee = task.assignee if task.assignee else "미정"
    deadline = task.deadline if task.deadline else "미정"

    return (
        f"- 업무: {task.task}\n"
        f"  담당자: {assignee}\n"
        f"  마감일: {deadline}\n"
        f"  상태: {task.status}"
    )


def _make_notion_children(request: NotionSaveRequest) -> List[dict]:
    """
    Notion 페이지 본문에 들어갈 블록들을 생성
    """
    children = []

    # 요약
    if request.summary:
        children.append(_heading_block("요약"))
        children.append(_plain_text_block(request.summary))

    # 원본 내용
    if request.content:
        children.append(_heading_block("원본 내용"))
        children.append(_plain_text_block(request.content[:1800]))

    # 할 일 목록
    if request.tasks:
        children.append(_heading_block("추출된 할 일"))

        for task in request.tasks:
            children.append(_plain_text_block(_task_to_text(task)))

    # 아무 내용도 없을 때
    if not children:
        children.append(_plain_text_block("저장할 내용이 없습니다."))

    return children


def _get_title_property_name() -> str:
    """
    Notion 데이터베이스에서 title 타입 속성 이름을 찾아오는 함수

    현재 DB에서는 '회의록 제목'이 title 속성이지만,
    혹시 이름이 바뀌어도 자동으로 찾기 위해 사용
    """
    notion = get_notion_client()

    database = notion.databases.retrieve(
        database_id=settings.NOTION_DATABASE_ID
    )

    properties = database.get("properties", {})

    for property_name, property_info in properties.items():
        if property_info.get("type") == "title":
            return property_name

    # 혹시 못 찾으면 기본값 사용
    return "회의록 제목"


def save_to_notion(request: NotionSaveRequest) -> NotionSaveResponse:
    """
    요약, 할 일, 문서 내용을 Notion 데이터베이스에 저장하는 함수
    """

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
            parent={
                "database_id": settings.NOTION_DATABASE_ID
            },
            properties={
                title_property_name: {
                    "title": [
                        {
                            "text": {
                                "content": request.title
                            }
                        }
                    ]
                },
                "요약": {
                    "rich_text": [
                        {
                            "text": {
                                "content": request.summary or ""
                            }
                        }
                    ]
                },
                "작성일": {
                    "date": {
                        "start": request.created_at
                    }
                },
                "상태": {
                    "select": {
                        "name": request.status
                    }
                }
            },
            children=_make_notion_children(request)
        )

        return NotionSaveResponse(
            status="success",
            notion_url=page.get("url"),
            error=None
        )

    except Exception as e:
        return NotionSaveResponse(
            status="error",
            notion_url=None,
            error=str(e)
        )