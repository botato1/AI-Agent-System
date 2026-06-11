from backend.schemas.agent_schema import AgentState
from backend.services.rag_service import rag_service
from backend.services.ollama_service import ollama_service


# RAG 검색 결과에서 context 문자열을 만드는 함수
# 검색된 문서 chunk들의 content만 모아서 하나의 문자열로 합침
def _build_rag_context(docs: list[dict]) -> str:
    return "\n\n".join(
        [
            doc.get("content", "")
            for doc in docs
            if doc.get("content")
        ]
    )


# 문서 검색이 필요한 경우 ChromaDB/RAG에서 관련 내용을 검색하는 노드
def rag_node(state: AgentState) -> AgentState:
    # RAG가 필요 없으면 검색하지 않고 다음 노드로 넘김
    if not state.get("need_rag", False):
        return {
            **state,
            "rag_context": state.get("rag_context") or "",
            "sources": state.get("sources") or [],
            "current_step": "rag_node",
            "error": state.get("error"),
        }

    user_message = state.get("user_message", "")        # 사용자가 입력한 질문
    target_document_id = state.get("target_document_id")    # 프론트에서 특정 문서를 선택했을 때 넘어오는 문서 ID
    target_filename = ollama_service.normalize_text(state.get("target_filename"))   # 사용자가 지정한 파일명 또는 프론트에서 선택한 파일명
    question_type = state.get("question_type", "general")   # classifier_node가 분류한 질문 타입

    # 검색할 때 특정 문서만 찾도록 filter 생성
    rag_filter = ollama_service.build_rag_filter(
        target_document_id=target_document_id,
        target_filename=target_filename,
        existing_filter=state.get("rag_filter"),
    )

    try:
        # 디버그 로그
        print(f"[rag_node] user_message: {user_message}")
        print(f"[rag_node] question_type: {question_type}")
        print(f"[rag_node] target_document_id: {target_document_id}")
        print(f"[rag_node] target_filename: {target_filename}")
        print(f"[rag_node] rag_filter: {rag_filter}")

        # 1차 검색: question_type 기반 컬렉션 + document_id/filename filter 검색
        result = rag_service.retrieve_relevant_knowledge_sync(
            query=user_message,
            top_k=5,
            filter=rag_filter,
            question_type=question_type,
        )

        # 검색 결과가 몇 개인지 출력
        print(f"[rag_node] first search count: {result.get('count', 0) if result else 0}")

        # 2차 fallback:
        # filename metadata가 없거나 한글 정규화 문제로 filter 검색 실패 시
        # 파일명 / 확장자 제거 파일명 / 사용자 질문으로 전체 컬렉션 검색 후 title 기준 필터링
        if target_filename and result and result.get("count", 0) == 0:
            fallback_queries = [
                target_filename,
                target_filename.rsplit(".", 1)[0] if "." in target_filename else target_filename,
                user_message,
            ]

            for fallback_query in fallback_queries:
                fallback_result = rag_service.retrieve_relevant_knowledge_sync(
                    query=fallback_query,
                    top_k=50,
                    filter=None,
                    question_type="general",        # task_extract로 보내면 meeting_collection만 검색할 수 있어 general로 보내 전체 collection을 볼 수 있도록 함
                )
                
                # fallback 결과 로그
                print(
                    f"[rag_node] fallback query: {fallback_query}, "
                    f"raw count: {fallback_result.get('count', 0) if fallback_result else 0}"
                )

                # fallba
                if not fallback_result or fallback_result.get("status") != "success":
                    continue

                filtered_docs = [
                    doc
                    for doc in fallback_result.get("data", [])
                    if ollama_service.filename_in_title(
                        target_filename,
                        doc.get("title"),
                    )
                ]

                print(f"[rag_node] fallback filtered count: {len(filtered_docs)}")

                if filtered_docs:
                    result = {
                        **fallback_result,
                        "count": len(filtered_docs),
                        "data": filtered_docs,
                    }
                    break

        if not result or result.get("status") != "success" or result.get("count", 0) == 0:
            return {
                **state,
                "rag_context": "",
                "sources": [],
                "rag_filter": rag_filter,
                "current_step": "rag_node",
                "error": state.get("error"),
            }

        docs = ollama_service.deduplicate_docs(result.get("data", []))
        rag_context = _build_rag_context(docs)
        sources = ollama_service.format_sources(docs)

        return {
            **state,
            "rag_context": rag_context,
            "sources": sources,
            "rag_filter": rag_filter,
            "current_step": "rag_node",
            "error": None,
        }

    except Exception as e:
        print(f"[rag_node 에러]: {str(e)}")

        return {
            **state,
            "rag_context": "",
            "sources": [],
            "rag_filter": rag_filter,
            "current_step": "rag_node",
            "error": str(e),
        }