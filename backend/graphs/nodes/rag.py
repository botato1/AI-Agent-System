from backend.schemas.agent_schema import AgentState
from backend.services.rag_service import rag_service


# 검색된 문서 목록을 LLM에 전달할 RAG 문맥 문자열로 변환
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


# 검색된 문서 목록을 프론트에 반환할 sources 형식으로 변환
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


# rag_filter를 결정. classifier_node에서 생성된 필터를 우선 사용
def _resolve_rag_filter(state: AgentState) -> dict | None:
    rag_filter = state.get("rag_filter")
    target_document_id = state.get("target_document_id")
    target_filename = state.get("target_filename")

    if not rag_filter and target_document_id:
        return {"document_id": target_document_id}

    if not rag_filter and target_filename:
        return {"filename": target_filename}

    return rag_filter


# RAG 검색을 수행하고 결과를 AgentState에 저장하는 LangGraph 노드
def rag_node(state: AgentState) -> AgentState:
    if not state.get("need_rag", False):
        return {
            **state,
            "rag_context": state.get("rag_context") or "",
            "rag_search_result": state.get("rag_search_result"),
            "retrieved_docs": state.get("retrieved_docs") or [],
            "low_confidence": state.get("low_confidence", False),
            "sources": state.get("sources") or [],
            "current_step": "rag_node",
            "error": state.get("error"),
        }

    user_message = state.get("user_message", "")
    question_type = state.get("question_type", "general_answer")
    rag_filter = _resolve_rag_filter(state)

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
            or rag_result.get("low_confidence", False)
        )

        return {
            **state,
            "rag_context": _build_rag_context(retrieved_docs),
            "rag_search_result": rag_result,
            "retrieved_docs": retrieved_docs,
            "low_confidence": low_confidence,
            "sources": _build_sources(retrieved_docs),
            "rag_filter": rag_filter,
            "current_step": "rag_node",
            "error": rag_result.get("error"),
        }

    except Exception as e:
        return {
            **state,
            "rag_context": "",
            "rag_search_result": {
                "status": "error",
                "query": user_message,
                "count": 0,
                "data": [],
                "low_confidence": True,
                "error": str(e),
            },
            "retrieved_docs": [],
            "low_confidence": True,
            "sources": [],
            "rag_filter": rag_filter,
            "current_step": "rag_node",
            "error": str(e),
        }