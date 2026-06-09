import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from langchain_ollama import ChatOllama

from backend.schemas.agent_schema import AgentState
from backend.schemas.notion_schema import NotionSaveRequest
from backend.schemas.task_schema import TaskItemSchema
from backend.services.notion_service import save_to_notion

load_dotenv()

llm = ChatOllama(
    model="qwen2.5:7b",
    temperature=0.3,
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
)

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
        "error": "Notion 저장 결과 형식을 변환할 수 없습니다."
    }

def _extract_requested_title(user_message: str) -> str | None:
    patterns = [
        r"제목은\s*(.+?)(?:이라고|라고|으로|로)\s*해줘",
        r"제목을\s*(.+?)(?:이라고|라고|으로|로)\s*해줘",
        r"제목은\s*(.+)$",
        r"제목을\s*(.+)$",
    ]

    for pattern in patterns:
        match = re.search(pattern, user_message)
        if match:
            return match.group(1).strip()

    return None

def _generate_summary_for_notion(content: str) -> str | None:
    if not content or not content.strip():
        return None

    prompt = f"""
아래 원본 내용을 Notion에 함께 저장할 요약문으로 정리해줘.

[규칙]
- 원본에 없는 내용은 추가하지 마라.
- 핵심 내용만 간결하게 정리해라.
- 한국어로 작성해라.
- 제목은 만들지 마라.
- 3~5개 bullet point 또는 짧은 문단으로 작성해라.

원본 내용:
{content}

요약:
"""

    try:
        response = llm.invoke(prompt)
        return response.content.strip()
    except Exception as e:
        print(f"[notion_node 요약 생성 에러]: {str(e)}")
        return None

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
        final_answer = state.get("final_answer")
        memory_context = state.get("memory_context")
        save_target_content = state.get("save_target_content")

        room_id = state.get("room_id", "")
        user_message = state.get("user_message", "")
        source = state.get("source", "text")
        created_at = _get_created_at(state.get("created_at"))
        summary = state.get("summary")
        tasks = state.get("tasks", [])
        document_json = state.get("document_json") or {}

        requested_title = _extract_requested_title(user_message)

        title = (requested_title
                 or document_json.get("title")
                 or "AI Agent 저장 결과"
                 )

        # Notion 저장 대상 content 결정
        # "방금 답변을 저장" 같은 요청이면 memory_context를 우선 저장한다.
        existing_summary = state.get("summary")
        rag_context = state.get("rag_context")

        if save_target_content:
            content = save_target_content
        elif state.get("need_task_extract") and rag_context:
            content = rag_context
        elif state.get("need_memory") and memory_context:
            content = memory_context
        elif document_json.get("content"):
            content = document_json.get("content")
        elif final_answer and final_answer != "Notion 저장 요청을 확인했습니다. 저장을 진행하겠습니다.":
            content = final_answer
        else:
            content = user_message

        summary = existing_summary or _generate_summary_for_notion(content)

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
            content=content,      # 원본 내용
            summary=summary,      # LLM 요약
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