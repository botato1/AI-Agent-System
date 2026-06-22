import re
from datetime import datetime
from zoneinfo import ZoneInfo

from backend.schemas.agent_schema import AgentState
from backend.schemas.notion_schema import NotionSaveRequest
from backend.schemas.task_schema import TaskItemSchema
from backend.services.notion_service import save_to_notion
from backend.services.ollama_service import ollama_service


# AgentState 안의 tasks는 dict 리스트로 들어올 수 있으므로 TaskItemSchema 리스트로 변환
def _convert_tasks(tasks: list) -> list[TaskItemSchema]:
    converted_tasks = []

    for task in tasks or []:
        if isinstance(task, TaskItemSchema):
            converted_tasks.append(task)
        elif isinstance(task, dict):
            converted_tasks.append(TaskItemSchema(**task))

    return converted_tasks


# created_at이 비어 있을 때 사용할 기본 날짜 생성
def _get_created_at(created_at: str | None) -> str:
    if created_at:
        return created_at

    return datetime.now(ZoneInfo("Asia/Seoul")).isoformat()


# NotionSaveResponse를 dict로 변환
def _to_dict(result):
    if hasattr(result, "model_dump"):
        return result.model_dump()

    if isinstance(result, dict):
        return result

    return {
        "status": "error",
        "notion_url": None,
        "error": "Notion 저장 결과 형식을 변환할 수 없습니다.",
    }


# 사용자 메시지에서 저장 제목을 추출하는 함수
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


# 이전 대화 중 가장 최근 assistant 답변을 가져오는 함수
def _get_latest_assistant_message(messages: list) -> str | None:
    for message in reversed(messages or []):
        if not isinstance(message, dict):
            continue

        role = message.get("role")
        content = message.get("content")

        if role == "assistant" and content:
            return str(content).strip()

    return None


# tasks 리스트를 Notion에 저장하기 좋은 문자열로 변환
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


# LangGraph에서 Notion 저장을 담당하는 노드
def notion_node(state: AgentState) -> AgentState:
    # 사용자가 Notion 저장을 원하지 않으면 저장하지 않음
    if not state.get("need_notion_save", False):
        return {
            **state,
            "notion_result": {
                "status": "skipped",
                "notion_url": None,
                "error": None,
            },
            "current_step": "notion_node",
            "error": state.get("error"),
        }

    try:
        final_answer = state.get("final_answer")
        memory_context = state.get("memory_context")
        rag_context = state.get("rag_context")
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

        # 현재 요청이 "방금 추출한 내용/이전 대화 결과를 노션에 저장"하는 흐름인지 판단
        is_memory_based_notion_save = (
            state.get("need_notion_save", False)
            and state.get("need_memory", False)
            and not state.get("need_rag", False)
        )

        # 회의록/task 추출 저장 요청인데 실제 문서 내용이나 추출된 할 일이 없으면 저장하지 않음
        # 단, memory 기반 Notion 저장은 이전 assistant 답변을 저장할 수 있으므로 여기서 막지 않음
        if state.get("need_task_extract") and not is_memory_based_notion_save:
            has_source_content = bool((rag_context or "").strip()) or bool(
                (document_json.get("content") or "").strip()
            )
            has_tasks = bool(tasks)

            if not has_source_content:
                return {
                    **state,
                    "notion_result": {
                        "status": "error",
                        "notion_url": None,
                        "error": "회의록 내용을 찾지 못해 Notion에 저장하지 않았습니다.",
                    },
                    "final_answer": "회의록 내용을 찾지 못해 Notion에 저장하지 않았습니다. 회의록 파일이 선택되어 있는지 확인해 주세요.",
                    "current_step": "notion_node",
                    "error": "rag_context_empty",
                }

            if not has_tasks:
                return {
                    **state,
                    "notion_result": {
                        "status": "error",
                        "notion_url": None,
                        "error": "추출된 할 일이 없어 Notion에 저장하지 않았습니다.",
                    },
                    "final_answer": "추출된 할 일이 없어 Notion에 저장하지 않았습니다. 회의록 내용에서 담당자, 할 일, 마감일 정보를 찾을 수 있는지 확인해 주세요.",
                    "current_step": "notion_node",
                    "error": "tasks_empty",
                }

        requested_title = _extract_requested_title(user_message)

        # 제목 결정
        if requested_title:
            title = requested_title
        elif is_memory_based_notion_save:
            title = "대화 기반 할 일 목록"
        elif document_json.get("title"):
            title = document_json.get("title")
        elif state.get("target_filename"):
            title = state.get("target_filename")
        else:
            title = "AI Agent 저장 결과"

        # Notion 저장 대상 content 결정
        # 1. 현재 state에 tasks가 있으면 tasks를 가장 우선 저장
        if formatted_tasks:
            content = formatted_tasks

        # 2. "방금 추출한 할 일 목록을 노션에 저장해줘" 같은 요청이면
        #    사용자 요청 문장이 아니라 직전 assistant 답변을 저장해야 함
        elif is_memory_based_notion_save and latest_assistant_message:
            content = latest_assistant_message

        # 3. save_target_content가 있으면 우선 사용
        elif save_target_content:
            content = save_target_content

        # 4. 문서/회의록 기반 task 저장
        elif state.get("need_task_extract") and document_json.get("content"):
            content = document_json.get("content")

        elif state.get("need_task_extract") and rag_context:
            content = rag_context

        # 5. memory_context가 있으면 사용
        elif state.get("need_memory") and memory_context:
            content = memory_context

        # 6. RAG / 문서 내용
        elif rag_context:
            content = rag_context

        elif document_json.get("content"):
            content = document_json.get("content")

        # 7. 최종 답변이 있으면 사용
        elif final_answer and final_answer != "Notion 저장 요청을 확인했습니다. 저장을 진행하겠습니다.":
            content = final_answer

        # 8. 진짜 아무것도 없을 때만 user_message 저장
        else:
            content = user_message

        summary = (
            existing_summary
            or document_json.get("summary")
            or ollama_service.generate_summary_for_notion(content)
        )

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

        if notion_result.get("status") == "success":
            notion_url = notion_result.get("notion_url")

            final_answer = (
                f"Notion에 저장했습니다.\n{notion_url}"
                if notion_url
                else "Notion에 저장했습니다."
            )

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
            "notion_result": {
                "status": "error",
                "notion_url": None,
                "error": str(e),
            },
            "final_answer": f"Notion 저장 중 오류가 발생했습니다.\n{str(e)}",
            "current_step": "notion_node",
            "error": str(e),
        }