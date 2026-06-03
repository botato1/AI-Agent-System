from backend.schemas.agent_schema import AgentState


def rag_node(state: AgentState) -> AgentState:
    user_message = state["user_message"]

    # TODO: ChromaDB에서 관련 문서 검색 로직 (rag 모듈 완성 후 연결)
    # 지금은 빈 컨텍스트로 반환
    rag_context = "관련 문서 없음"
    sources = []

    return {
        **state,
        "rag_context": rag_context,
        "sources": sources,
    }