from backend.schemas.agent_schema import AgentState
from backend.db.crud import get_messages


def memory_node(state: AgentState) -> AgentState:
    if not state.get("need_memory", False):
        return {
            **state,
            "memory_context": state.get("memory_context") or "",
            "save_target_content":state.get("save_target_content"),
            "current_step": "memory_node",
            "error": None,
        }
    
    room_id = state.get("room_id", "")

    try:
        messages = get_messages(room_id)
        memory_context = ""
        save_target_content = None

        if messages:
            memory_lines = []

            for row in messages:
                # row[1] = role
                # row[2] = content
                role = row[1]
                content = row[2]

                memory_lines.append(f"{role}: {content}")

                # 가장 최근 assistant 답변을 저장 대상으로 사용
                if role == "assistant":
                    save_target_content = content

            memory_context = "\n".join(memory_lines)

        return {
            **state,
            "memory_context": memory_context,
            "save_target_content": save_target_content,
            "current_step": "memory_node",
            "error": None,
        }

    except Exception as e:
        print(f"[memory_node 에러]: {str(e)}")
        
        return {
            **state,
            "memory_context": "",
            "save_target_content" : None,
            "current_step" : "memory_node",
            "error" : str(e)
        }

