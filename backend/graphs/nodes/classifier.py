from backend.schemas.agent_schema import AgentState
from backend.services.ollama_service import ollama_service


# 사용자 메시지를 분석해서 memory, rag, task_extract, notion_save 필요 여부를 판단하는 노드
def classifier_node(state: AgentState) -> AgentState:
    user_message = state.get("user_message", "")

    try:
        classified = ollama_service.classify_for_graph(user_message)

        target_document_id = state.get("target_document_id")
        target_filename = ollama_service.normalize_text(
            state.get("target_filename") or classified.get("target_filename")
        )

        rag_filter = state.get("rag_filter")

        # 프론트에서 선택 문서가 넘어온 경우 document_id 우선
        if target_document_id:
            rag_filter = {"document_id": target_document_id}
            classified["need_rag"] = True

        # 파일명이 명시된 경우 filename filter 준비
        elif target_filename:
            rag_filter = {"filename": target_filename}
            classified["need_rag"] = True

        need_general_answer = not (
            classified.get("need_memory", False)
            or classified.get("need_rag", False)
            or classified.get("need_task_extract", False)
            or classified.get("need_notion_save", False)
        )

        return {
            **state,
            "question_type": classified.get("question_type", "general"),
            "need_general_answer": need_general_answer,
            "need_memory": classified.get("need_memory", False),
            "need_rag": classified.get("need_rag", False),
            "need_task_extract": classified.get("need_task_extract", False),
            "need_notion_save": classified.get("need_notion_save", False),
            "target_document_id": target_document_id,
            "target_filename": target_filename,
            "rag_filter": rag_filter,
            "current_step": "classifier_node",
            "error": None,
        }

    except Exception as e:
        return {
            **state,
            "question_type": "general",
            "need_general_answer": True,
            "need_memory": False,
            "need_rag": False,
            "need_task_extract": False,
            "need_notion_save": False,
            "target_document_id": state.get("target_document_id"),
            "target_filename": state.get("target_filename"),
            "rag_filter": state.get("rag_filter"),
            "current_step": "classifier_node",
            "error": str(e),
        }