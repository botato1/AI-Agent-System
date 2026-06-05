from datetime import datetime

from backend.schemas.agent_schema import AgentState
from backend.schemas.notion_schema import NotionSaveRequest
from backend.schemas.task_schema import TaskItemSchema
from backend.services.notion_service import save_to_notion

# AgentState 안의 tasks는 dict 리스트로 들어올 수 있으므로 TaskItemSchema 리스트로 변환
def _convert_tasks(tasks: list) -> list[TaskItemSchema]:
    converted_tasks = []

    for task in tasks:
        if isinstance(task, TaskItemSchema):
            converted_tasks.append(task)
        elif isinstance(task, dict):
            converted_tasks.append(TaskItemSchema(**task))

    return converted_tasks

# created_at이 비어 있을 때 사용할 기본 날짜 생성
def _get_created_at(created_at: str | None) -> str:
    if created_at:
        return created_at

    return datetime.now().date().isoformat()


# NotionSaveResponse를 dict로 변환
def _to_dict(result):
    if hasattr(result, "model_dump"):
        return result.model_dump()

    if isinstance(result, dict):
        return result

    return {
        "status": "error",
        "notion_url": None,
        "error": "Notion 저장 결과 형식을 변환할 수 없습니다."
    }

# LangGraph에서 Notion 저장을 담당하는 노드
def notion_node(state: AgentState) -> AgentState:

    # 사용자가 Notion 저장을 원하지 않으면 저장하지 않음
    if not state.get("need_notion_save", False):
        notion_result = {
            "status": "skipped",
            "notion_url": None,
            "error": None,
        }

        return {
            **state,
            "notion_result": notion_result,
            "current_step": "notion_node",
            "error": None,
        }

    try:
        room_id = state.get("room_id", "")
        user_message = state.get("user_message", "")
        source = state.get("source", "text")
        created_at = _get_created_at(state.get("created_at"))
        summary = state.get("summary")
        tasks = state.get("tasks", [])
        document_json = state.get("document_json") or {}

        title = document_json.get("title") or user_message[:50] or "AI Agent 저장 결과"
        content = document_json.get("content") or user_message
        document_type = document_json.get("type") or "meeting"
        language = document_json.get("language") or "ko"
        tags = document_json.get("tags") or []
        status = document_json.get("status") or "processed"
        chroma_id = document_json.get("chroma_id")
        user_edited = document_json.get("user_edited", False)
        error = document_json.get("error")

        notion_request = NotionSaveRequest(
            id=document_json.get("id"),
            title=title,
            type=document_type,
            source=source,
            content=content,
            summary=summary,
            language=language,
            created_at=created_at,
            tags=tags,
            status=status,
            chroma_id=chroma_id,
            user_edited=user_edited,
            error=error,
            room_id=room_id,
            tasks=_convert_tasks(tasks),
        )

        result = save_to_notion(notion_request)
        notion_result = _to_dict(result)

        return {
            **state,
            "notion_result": notion_result,
            "current_step": "notion_node",
            "error": notion_result.get("error")
        }

    except Exception as e:
        return {
            **state,
            "notion_result": {
                "status": "error",
                "notion_url": None,
                "error": str(e),
            },
            "current_step": "notion_node",
            "error": str(e),
        }