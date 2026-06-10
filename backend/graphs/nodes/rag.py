import asyncio
import unicodedata
from concurrent.futures import ThreadPoolExecutor

from backend.schemas.agent_schema import AgentState
from backend.services.rag_service import rag_service


# 비동기 RAG 함수를 동기 LangGraph 노드에서 안전하게 실행하는 헬퍼 함수
def _run_async(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(lambda: asyncio.run(coro))
        return future.result()


def build_rag_filter(state: AgentState) -> dict | None:
    """
    AgentState에 저장된 문서 식별 정보를 기준으로 RAG 검색 filter를 만든다.

    우선순위:
    1. rag_filter
    2. target_document_id
    3. target_filename
    """
    if state.get("rag_filter"):
        return state.get("rag_filter")

    if state.get("target_document_id"):
        return {"document_id": state.get("target_document_id")}

    if state.get("target_filename"):
        return {"filename": state.get("target_filename")}

    return None


def normalize_text(value: str | None) -> str:
    if not value:
        return ""

    return unicodedata.normalize("NFC", value).strip()


def build_rag_context(docs: list[dict]) -> str:
    return "\n\n".join(
        [
            doc.get("content", "")
            for doc in docs
            if doc.get("content")
        ]
    )


def build_sources(docs: list[dict]) -> list[dict]:
    return [
        {
            "id": doc.get("id")
            or doc.get("document_id")
            or doc.get("chroma_id"),
            "document_id": doc.get("document_id"),
            "filename": doc.get("filename"),
            "title": doc.get("title"),
            "source": doc.get("source")
            or doc.get("filename")
            or doc.get("title"),
            "score": doc.get("score"),
        }
        for doc in docs
    ]


def rag_node(state: AgentState) -> AgentState:
    # RAG가 필요 없으면 검색하지 않고 바로 다음 노드로 넘긴다.
    if not state.get("need_rag", False):
        return {
            **state,
            "rag_context": state.get("rag_context") or "",
            "sources": state.get("sources", []),
            "current_step": "rag_node",
            "error": state.get("error"),
        }

    user_message = state.get("user_message", "")
    rag_filter = build_rag_filter(state)
    target_filename = state.get("target_filename")

    try:
        print("[rag_node] user_message:", user_message)
        print("[rag_node] target_filename:", target_filename)
        print("[rag_node] rag_filter:", rag_filter)

        # 1차 검색: document_id / filename filter 기반 검색
        result = _run_async(
            rag_service.retrieve_relevant_knowledge(
                query=user_message,
                top_k=5,
                filter=rag_filter,
            )
        )

        print("[rag_node] first search count:", result.get("count"))

        # 임시 fallback:
        # metadata에 filename이 없고 title에 "파일명.pdf - chunk n"만 있는 경우
        if target_filename and result.get("count", 0) == 0:
            fallback_result = _run_async(
                rag_service.retrieve_relevant_knowledge(
                    query=target_filename,
                    top_k=50,
                    filter=None,
                )
            )

            if fallback_result.get("status") == "success":
                normalized_target_filename = normalize_text(target_filename)

                filtered_docs = [
                    doc
                    for doc in fallback_result.get("data", [])
                    if normalized_target_filename in normalize_text(doc.get("title"))
                ]

                result = {
                    **fallback_result,
                    "count": len(filtered_docs),
                    "data": filtered_docs,
                }

        if result.get("status") == "success" and result.get("count", 0) > 0:
            docs = result.get("data", [])
            rag_context = build_rag_context(docs)
            sources = build_sources(docs)

        else:
            rag_context = ""
            sources = []

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