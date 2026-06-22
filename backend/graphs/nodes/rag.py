from backend.schemas.agent_schema import AgentState
from backend.services.rag_service import rag_service


# 검색된 문서 목록을 LLM에 전달할 RAG 문맥 문자열로 변환하는 함수
def _build_rag_context(retrieved_docs: list[dict]) -> str:
    contents = []

    for index, doc in enumerate(retrieved_docs, start=1):
        content = (doc.get("content") or "").strip()
        if not content:
            continue

        title = doc.get("title") or doc.get("filename") or f"검색 결과 {index}"
        collection = doc.get("collection") or ""
        score = doc.get("score")

        contents.append(
            f"[검색 결과 {index}] {title}\n"
            f"- collection: {collection}\n"
            f"- score: {score}\n"
            f"{content}"
        )

    return "\n\n".join(contents)


# 검색된 문서 목록을 프론트에 반환할 sources 형식으로 변환하는 함수
def _build_sources(retrieved_docs: list[dict]) -> list[dict]:
    return [
        {
            "id": doc.get("document_id") or doc.get("id"),
            "source": doc.get("source") or "rag",
            "title": doc.get("title") or doc.get("filename") or "검색 문서",
            "score": doc.get("score"),
            "collection": doc.get("collection"),
            "filename": doc.get("filename"),
            "chunk_index": doc.get("chunk_index"),
            "room_id": doc.get("room_id"),
        }
        for doc in retrieved_docs
    ]


# RAG가 필요한 질문이면 rag_service를 호출해 검색 결과를 AgentState에 저장하는 노드
def rag_node(state: AgentState) -> AgentState:
    if not state.get("need_rag", False):
        return {
            **state,
            "rag_context": state.get("rag_context") or "",
            "retrieved_docs": state.get("retrieved_docs") or [],
            "low_confidence": state.get("low_confidence", False),
            "sources": state.get("sources") or [],
            "current_step": "rag_node",
            "error": state.get("error"),
        }

    user_message = state.get("user_message", "")
    target_document_id = state.get("target_document_id")
    target_filename = state.get("target_filename")
    question_type = state.get("question_type", "general_answer")

    rag_filter = (
        {"document_id": target_document_id}
        if target_document_id
        else None
    )

    print(f"[rag_node] user_message: {user_message}")
    print(f"[rag_node] question_type: {question_type}")
    print(f"[rag_node] target_document_id: {target_document_id}")
    print(f"[rag_node] target_filename: {target_filename}")
    print(f"[rag_node] rag_filter: {rag_filter}")

    try:
        rag_result = rag_service.retrieve_relevant_knowledge(
            query=user_message,
            original_query=user_message,
            top_k=5,
            filter=rag_filter,
            question_type=question_type,
        )

        retrieved_docs = rag_result.get("data") or []

        low_confidence = (
            rag_result.get("status") != "success"
            or rag_result.get("count", 0) == 0
        )

        rag_context = _build_rag_context(retrieved_docs)
        sources = _build_sources(retrieved_docs)

        return {
            **state,
            "rag_context": rag_context,
            "retrieved_docs": retrieved_docs,
            "low_confidence": low_confidence,
            "sources": sources,
            "rag_filter": rag_filter,
            "current_step": "rag_node",
            "error": rag_result.get("error"),
        }

    except Exception as e:
        print(f"[rag_node 에러]: {str(e)}")

        return {
            **state,
            "rag_context": "",
            "retrieved_docs": [],
            "low_confidence": True,
            "sources": [],
            "rag_filter": rag_filter,
            "current_step": "rag_node",
            "error": str(e),
        }