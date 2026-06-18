from backend.schemas.agent_schema import AgentState
from backend.db.crud import get_messages


# sqlite3.Row 또는 tuple/list 모두 대응하기 위한 안전 접근 함수
def _get_value(row, key: str, index: int, default=None):
    try:
        return row[key]
    except Exception:
        try:
            return row[index]
        except Exception:
            return default


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

            # task_from_memory에서는 assistant가 생성한 답변을 다시 추출 재료로 쓰지 않음
            # 그래야 LLM이 이전 AI 답변을 근거로 없는 담당자/마감일을 만들어내는 문제를 줄일 수 있음
            if role == "user":
                # 현재 요청문 자체는 제외
                # 예: "지금까지 대화에서 해야 할 일 정리해줘"
                is_extract_request = (
                     content == current_user_message
                     and any(keyword in content for keyword in [
                          "지금까지",
                          "대화에서",
                          "대화 내용",
                          "해야 할 일 정리",
                          "할 일 정리",
                          "업무 정리",
                          "정리해줘",
                          "추출해줘",
                    ])
                )
                if is_extract_request:
                    continue

                memory_lines.append(f"user: {content}")

            # 가장 최근 assistant 답변은 Notion 저장 대상 후보로만 유지
            # 단, memory_context에는 넣지 않음
            if (
                role == "assistant"
                and not content.startswith("Notion에 저장했습니다.")
                and "Notion 저장 중 오류가 발생했습니다" not in content
            ):
                last_assistant_answer = content

        memory_context = "\n".join(memory_lines)

        return {
            **state,
            "memory_context": memory_context,
            "save_target_content": last_assistant_answer,
            "current_step": "memory_node",
            "error": state.get("error"),
        }

    except Exception as e:
        print(f"[memory_node 에러]: {str(e)}")

        return {
            **state,
            "memory_context": "",
            "save_target_content": None,
            "current_step": "memory_node",
            "error": str(e),
        }