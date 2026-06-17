from backend.schemas.agent_schema import AgentState
from backend.db.crud import get_document_by_id


# 문서 검색이 필요한 경우 SQLite documents 테이블에서 content_markdown을 조회하는 노드
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

    user_message = state.get("user_message", "")
    target_document_id = state.get("target_document_id")
    target_filename = state.get("target_filename")
    question_type = state.get("question_type", "general_answer")

    # 디버그용 print : 서버 안정화 후 삭제 예정
    print(f"[rag_node] user_message: {user_message}")
    print(f"[rag_node] question_type: {question_type}")
    print(f"[rag_node] target_document_id: {target_document_id}")
    print(f"[rag_node] target_filename: {target_filename}")

    # 1. target_document_id가 없으면 문서를 찾을 수 없음
    if not target_document_id:
        return {
            **state,
            "rag_context": "",
            "sources": [],
            "rag_filter": None,
            "current_step": "rag_node",
            "error": "target_document_id_missing",
        }

    try:
        # 2. documents 테이블에서 document_id 기준으로 문서 조회
        document = get_document_by_id(target_document_id)

        if not document:
            return {
                **state,
                "rag_context": "",
                "sources": [],
                "rag_filter": {"document_id": target_document_id},
                "current_step": "rag_node",
                "error": "document_not_found",
            }

        # 3. content_markdown을 RAG context로 사용
        content_markdown = document.get("content_markdown") or ""

        if not content_markdown.strip():
            return {
                **state,
                "rag_context": "",
                "sources": [],
                "rag_filter": {"document_id": target_document_id},
                "current_step": "rag_node",
                "error": "content_markdown_empty",
            }

        # 4. sources 생성
        sources = [
            {
                "id": document.get("id"),
                "source": document.get("source") or "document",
                "title": document.get("title") or target_filename or "문서",
                "score": None,
            }
        ]

        return {
            **state,
            "rag_context": content_markdown,
            "sources": sources,
            "rag_filter": {"document_id": target_document_id},
            "current_step": "rag_node",
            "error": None,
        }

    except Exception as e:
        print(f"[rag_node 에러]: {str(e)}")

        return {
            **state,
            "rag_context": "",
            "sources": [],
            "rag_filter": {"document_id": target_document_id},
            "current_step": "rag_node",
            "error": str(e),
        }