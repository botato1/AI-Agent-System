from backend.schemas.agent_schema import AgentState


def memory_node(state: AgentState) -> AgentState:
    room_id = state["room_id"]

    # TODO: SQLite에서 이전 대화 기록 가져오는 로직 (db 모듈 완성 후 연결)
    # 지금은 빈 컨텍스트로 반환
    memory_context = f"[room_id: {room_id}] 이전 대화 기록 없음"

    return {
        **state,
        "memory_context": memory_context,
    }