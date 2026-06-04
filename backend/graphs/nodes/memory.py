from backend.schemas.agent_schema import AgentState
from backend.db.crud import get_messages


def memory_node(state: AgentState) -> AgentState:
    room_id = state["room_id"]

    try:
        messages = get_messages(room_id)
        if messages:
            memory_context = "\n".join([f"{row[0]}: {row[1]}" for row in messages])
        else:
            memory_context = ""

    except Exception as e:
        print(f"[memory_node 에러]: {str(e)}")
        memory_context = ""

    return {
        **state,
        "memory_context": memory_context,
    }