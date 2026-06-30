from backend.schemas.agent_schema import AgentState
from backend.db.crud import get_messages


MEMORY_SKIP_KEYWORDS = [
    "지금까지", "대화에서", "대화 내용",
    "해야 할 일 정리", "할 일 정리", "업무 정리",
    "정리해줘", "추출해줘",
]

# sqlite3.Row 또는 tuple/list 모두 대응하는 안전 접근 함수
def _get_value(row, key: str, index: int, default=None):
    try:
        return row[key]
    except Exception:
        try:
            return row[index]
        except Exception:
            return default


# 현재 메시지가 할 일 추출 요청인지 확인
def _is_extract_request(content: str, current_user_message: str) -> bool:
    return content == current_user_message and any(
        keyword in content for keyword in MEMORY_SKIP_KEYWORDS
    )

# Notion 저장 결과 메시지를 제외한 유효한 assistant 답변인지 확인
def _is_valid_assistant_answer(content: str) -> bool:
    return (
        not content.startswith("Notion에 저장했습니다.")
        and "Notion 저장 중 오류가 발생했습니다" not in content
    )

# 대화 기록에서 memory_context와 Notion 저장 대상 콘텐츠를 추출하는 LangGraph 노드
def memory_node(state: AgentState) -> AgentState:
    if not state.get("need_memory", False):
        return {
            **state,
            "memory_context": state.get("memory_context") or "",
            "save_target_content": state.get("save_target_content"),
            "current_step": "memory_node",
            "error": state.get("error"),
        }

    room_id = state.get("room_id", "")
    current_user_message = (state.get("user_message") or "").strip()

    try:
        messages = get_messages(room_id)

        memory_lines = []
        last_assistant_answer = None

        for row in messages:
            role = _get_value(row, "role", 1, "")
            content = _get_value(row, "content", 2, "")

            if not role or not content:
                continue

            content = str(content).strip()

            if not content:
                continue

            if role == "user":
                if _is_extract_request(content, current_user_message):
                    continue
                memory_lines.append(f"user: {content}")

            if role == "assistant" and _is_valid_assistant_answer(content):
                last_assistant_answer = content

        return {
            **state,
            "memory_context": "\n".join(memory_lines),
            "save_target_content": last_assistant_answer,
            "current_step": "memory_node",
            "error": state.get("error"),
        }

    except Exception as e:
        return {
            **state,
            "memory_context": "",
            "save_target_content": None,
            "current_step": "memory_node",
            "error": str(e),
        }