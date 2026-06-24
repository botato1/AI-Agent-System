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
            "rag_search_result": state.get("rag_search_result"),
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

    # classifier_node 또는 chat_service에서 만들어둔 rag_filter를 우선 사용
    rag_filter = state.get("rag_filter")

    # 혹시 rag_filter가 비어 있는데 target_document_id가 있으면 보완
    if not rag_filter and target_document_id:
        rag_filter = {"document_id": target_document_id}

    # filename 필터까지 쓰는 구조라면 보완
    elif not rag_filter and target_filename:
        rag_filter = {"filename": target_filename}

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

        rag_context = _build_rag_context(retrieved_docs)
        sources = _build_sources(retrieved_docs)

        return {
            **state,

            # 기존 rag_context는 특정 문서 직접 조회/기존 answer 흐름 호환용
            "rag_context": rag_context,

            # rag_service.retrieve_relevant_knowledge() 반환값 전체
            # answer_node에서 generate_answer_for_graph(..., rag_search_result=...)로 전달
            "rag_search_result": rag_result,

            # 프론트 응답 / graph_data 표시용으로 유지
            "retrieved_docs": retrieved_docs,
            "low_confidence": low_confidence,
            "sources": sources,

            "rag_filter": rag_filter,
            "current_step": "rag_node",
            "error": rag_result.get("error"),
        }

    except Exception as e:
        error_result = {
            "status": "error",
            "query": user_message,
            "count": 0,
            "data": [],
            "low_confidence": True,
            "error": str(e),
        }

        return {
            **state,
            "rag_context": "",
            "rag_search_result": error_result,
            "retrieved_docs": [],
            "low_confidence": True,
            "sources": [],
            "rag_filter": rag_filter,
            "current_step": "rag_node",
            "error": str(e),
        }