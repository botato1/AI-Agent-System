import re
from datetime import datetime
from zoneinfo import ZoneInfo

from backend.schemas.agent_schema import AgentState
from backend.schemas.notion_schema import NotionSaveRequest
from backend.schemas.task_schema import TaskItemSchema
from backend.services.notion_service import save_to_notion
from backend.services.ollama_service import ollama_service


# AgentState의 tasks dict 리스트를 TaskItemSchema 리스트로 변환
def _convert_tasks(tasks: list) -> list[TaskItemSchema]:
    converted_tasks = []

    for task in tasks or []:
        if isinstance(task, TaskItemSchema):
            converted_tasks.append(task)
        elif isinstance(task, dict):
            converted_tasks.append(TaskItemSchema(**task))

    return converted_tasks


# created_at이 없을 때 현재 시각을 반환
def _get_created_at(created_at: str | None) -> str:
    if created_at:
        return created_at

    return datetime.now(ZoneInfo("Asia/Seoul")).isoformat()

# NotionSaveResponse를 dict로 변환
def _to_dict(result) -> dict:
    if hasattr(result, "model_dump"):
        return result.model_dump()

    if isinstance(result, dict):
        return result

    return {
        "status": "error",
        "notion_url": None,
        "error": "Notion 저장 결과 형식을 변환할 수 없습니다.",
    }

# 사용자 메시지에서 저장 제목을 추출
def _extract_requested_title(user_message: str) -> str | None:
    patterns = [
        r"저장\s*제목은\s*(.+?)(?:이라고|라고|으로|로)\s*해줘",
        r"제목은\s*(.+?)(?:이라고|라고|으로|로)\s*해줘",
        r"제목을\s*(.+?)(?:이라고|라고|으로|로)\s*해줘",
        r"저장\s*제목은\s*(.+)$",
        r"제목은\s*(.+)$",
        r"제목을\s*(.+)$",
    ]

    for pattern in patterns:
        match = re.search(pattern, user_message)
        if match:
            return match.group(1).strip()

    return None


# 이전 대화 중 가장 최근 assistant 답변을 반환
def _get_latest_assistant_message(messages: list) -> str | None:
    for message in reversed(messages or []):
        if not isinstance(message, dict):
            continue

        role = message.get("role")
        content = message.get("content")

        if role == "assistant" and content:
            return str(content).strip()

    return None

# tasks 리스트를 Notion 저장용 문자열로 변환
def _format_tasks_for_save(tasks: list) -> str:
    converted_tasks = _convert_tasks(tasks)

    if not converted_tasks:
        return ""

    lines = []

    for index, task in enumerate(converted_tasks, start=1):
        assignee = task.assignee or "미정"
        deadline = task.deadline or "미정"

        lines.append(
            f"{index}. {task.task}\n"
            f"   - 담당자: {assignee}\n"
            f"   - 마감일: {deadline}\n"
            f"   - 상태: {task.status}"
        )

    return "\n\n".join(lines)

# Notion 저장 제목을 우선순위에 따라 결정
def _resolve_notion_title(state: AgentState, requested_title: str | None, is_memory_based: bool, document_json: dict) -> str:
    if requested_title:
        return requested_title

    if is_memory_based:
        return "대화 기반 할 일 목록"

    if document_json.get("title"):
        return document_json.get("title")

    if state.get("target_filename"):
        return state.get("target_filename")

    return "AI Agent 저장 결과"

# Notion에 저장할 content를 우선순위에 따라 결정
def _resolve_notion_content(
    state: AgentState,
    formatted_tasks: str,
    is_memory_based: bool,
    latest_assistant_message: str | None,
    save_target_content: str | None,
    rag_context: str,
    memory_context: str,
    document_json: dict,
    final_answer: str | None,
    user_message: str,
) -> str:
    if formatted_tasks:
        return formatted_tasks

    if is_memory_based and latest_assistant_message:
        return latest_assistant_message

    if save_target_content:
        return save_target_content

    if state.get("need_task_extract") and document_json.get("content"):
        return document_json.get("content")

    if state.get("need_task_extract") and rag_context:
        return rag_context

    if state.get("need_memory") and memory_context:
        return memory_context

    if rag_context:
        return rag_context

    if document_json.get("content"):
        return document_json.get("content")

    if final_answer and final_answer != "Notion 저장 요청을 확인했습니다. 저장을 진행하겠습니다.":
        return final_answer

    return user_message

# task 저장 전 필수 조건을 검증한다. 오류 시 반환할 state dict를 반환
def _validate_task_save(state: AgentState, rag_context: str, document_json: dict, tasks: list) -> dict | None:
    has_source = bool(rag_context.strip()) or bool(
        (document_json.get("content") or "").strip()
    )

    if not has_source:
        return {
            **state,
            "notion_result": {"status": "error", "notion_url": None, "error": "회의록 내용을 찾지 못해 Notion에 저장하지 않았습니다."},
            "final_answer": "회의록 내용을 찾지 못해 Notion에 저장하지 않았습니다. 회의록 파일이 선택되어 있는지 확인해 주세요.",
            "current_step": "notion_node",
            "error": "rag_context_empty",
        }

    if not tasks:
        return {
            **state,
            "notion_result": {"status": "error", "notion_url": None, "error": "추출된 할 일이 없어 Notion에 저장하지 않았습니다."},
            "final_answer": "추출된 할 일이 없어 Notion에 저장하지 않았습니다. 회의록 내용에서 담당자, 할 일, 마감일 정보를 찾을 수 있는지 확인해 주세요.",
            "current_step": "notion_node",
            "error": "tasks_empty",
        }

    return None

# Notion 저장을 담당하는 LangGraph 노드
def notion_node(state: AgentState) -> AgentState:
    if not state.get("need_notion_save", False):
        return {
            **state,
            "notion_result": {"status": "skipped", "notion_url": None, "error": None},
            "current_step": "notion_node",
            "error": state.get("error"),
        }

    try:
        final_answer = state.get("final_answer")
        memory_context = state.get("memory_context") or ""
        rag_context = state.get("rag_context") or ""
        save_target_content = state.get("save_target_content")
        room_id = state.get("room_id", "")
        user_message = state.get("user_message", "")
        source = state.get("source", "text")
        created_at = _get_created_at(state.get("created_at"))
        existing_summary = state.get("summary")
        tasks = state.get("tasks", [])
        document_json = state.get("document_json") or {}
        messages = state.get("messages", [])

        latest_assistant_message = _get_latest_assistant_message(messages)
        formatted_tasks = _format_tasks_for_save(tasks)

        is_memory_based = (
            state.get("need_notion_save", False)
            and state.get("need_memory", False)
            and not state.get("need_rag", False)
        )

        if state.get("need_task_extract") and not is_memory_based:
            validation_error = _validate_task_save(state, rag_context, document_json, tasks)
            if validation_error:
                return validation_error

        title = _resolve_notion_title(
            state=state,
            requested_title=_extract_requested_title(user_message),
            is_memory_based=is_memory_based,
            document_json=document_json,
        )

        content = _resolve_notion_content(
            state=state,
            formatted_tasks=formatted_tasks,
            is_memory_based=is_memory_based,
            latest_assistant_message=latest_assistant_message,
            save_target_content=save_target_content,
            rag_context=rag_context,
            memory_context=memory_context,
            document_json=document_json,
            final_answer=final_answer,
            user_message=user_message,
        )

        summary = (
            existing_summary
            or document_json.get("summary")
            or ollama_service.generate_summary_for_notion(content)
        )

        notion_request = NotionSaveRequest(
            id=document_json.get("id"),
            title=title,
            type=document_json.get("type") or "meeting",
            source=source,
            content=content,
            summary=summary,
            language=document_json.get("language") or "ko",
            created_at=created_at,
            tags=document_json.get("tags") or [],
            status=document_json.get("status") or "processed",
            chroma_id=document_json.get("chroma_id"),
            user_edited=document_json.get("user_edited", False),
            error=document_json.get("error"),
            room_id=room_id,
            tasks=_convert_tasks(tasks),
        )

        result = save_to_notion(notion_request)
        notion_result = _to_dict(result)

        if notion_result.get("status") == "success":
            notion_url = notion_result.get("notion_url")
            final_answer = f"Notion에 저장했습니다.\n{notion_url}" if notion_url else "Notion에 저장했습니다."

            return {
                **state,
                "notion_result": notion_result,
                "summary": summary,
                "final_answer": final_answer,
                "current_step": "notion_node",
                "error": None,
            }

        final_answer = (
            f"Notion 저장 중 오류가 발생했습니다.\n{notion_result.get('error')}"
            if notion_result.get("error")
            else "Notion 저장 중 오류가 발생했습니다."
        )

        return {
            **state,
            "notion_result": notion_result,
            "summary": summary,
            "final_answer": final_answer,
            "current_step": "notion_node",
            "error": notion_result.get("error"),
        }

    except Exception as e:
        return {
            **state,
            "notion_result": {"status": "error", "notion_url": None, "error": str(e)},
            "final_answer": f"Notion 저장 중 오류가 발생했습니다.\n{str(e)}",
            "current_step": "notion_node",
            "error": str(e),
        }