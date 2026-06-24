from backend.schemas.agent_schema import AgentState
from backend.services.ollama_service import ollama_service


def _clean_extracted_tasks(
    tasks: list,
    document_id: str | None = None,
    room_id: str | None = None,
) -> list:
    """
    LLM이 추출한 tasks 중 빈 task를 제거한다.
    다양한 키 이름(task, title, content, 할 일, 다음 작업 등)을 표준 task 구조로 정규화한다.
    """
    if not tasks:
        return []

    cleaned_tasks = []

    for idx, task in enumerate(tasks, start=1):
        if not isinstance(task, dict):
            continue

        task_text = (
            task.get("task")
            or task.get("title")
            or task.get("content")
            or task.get("할 일")
            or task.get("업무")
            or task.get("작업")
            or task.get("다음 작업")
            or task.get("내용")
            or ""
        )
        task_text = str(task_text).strip()

        if not task_text:
            continue

        if task_text in {"할 일 없음", "없음", "해당 없음", "N/A", "null", "None"}:
            continue

        assignee = (
            task.get("assignee")
            or task.get("담당자")
            or task.get("담당")
            or task.get("owner")
            or None
        )

        deadline = (
            task.get("deadline")
            or task.get("마감일")
            or task.get("기한")
            or task.get("due_date")
            or task.get("due")
            or None
        )

        status = (
            task.get("status")
            or task.get("상태")
            or "todo"
        )

        priority = (
            task.get("priority")
            or task.get("우선순위")
            or "medium"
        )

        cleaned_task = {
            "task_id": task.get("task_id") or task.get("id") or f"task_{len(cleaned_tasks) + 1}",
            "task": task_text,
            "assignee": assignee,
            "deadline": deadline,
            "status": status,
            "priority": priority,
            "room_id": task.get("room_id") or room_id,
            "document_id": task.get("document_id") or document_id,
            "created_at": task.get("created_at"),
        }

        cleaned_tasks.append(cleaned_task)

    return cleaned_tasks


# LangGraph에서 문서 또는 대화 기반 할 일 추출을 담당하는 노드
def task_node(state: AgentState) -> AgentState:
    if not state.get("need_task_extract", False):
        return {
            **state,
            "tasks": state.get("tasks") or [],
            "current_step": "task_node",
            "error": state.get("error"),
        }

    rag_context = state.get("rag_context") or ""
    memory_context = state.get("memory_context") or ""
    document_json = state.get("document_json") or {}

    source_content = ""

    if isinstance(document_json, dict) and document_json.get("content"):
        source_content = document_json.get("content") or ""

    elif isinstance(document_json, dict) and document_json.get("content_markdown"):
        source_content = document_json.get("content_markdown") or ""

    elif rag_context.strip():
        source_content = rag_context

    elif memory_context.strip():
        source_content = memory_context

    else:
        return {
            **state,
            "tasks": [],
            "current_step": "task_node",
            "error": "task_source_empty",
        }

    try:
        extracted_tasks = ollama_service.extract_tasks_from_content(source_content)

        if extracted_tasks is None:
            extracted_tasks = []

        tasks = _clean_extracted_tasks(
            tasks=extracted_tasks,
            document_id=state.get("target_document_id"),
            room_id=state.get("room_id"),
        )

        return {
            **state,
            "tasks": tasks,
            "current_step": "task_node",
            "error": None,
        }

    except Exception as e:
        return {
            **state,
            "tasks": [],
            "current_step": "task_node",
            "error": str(e),
        }