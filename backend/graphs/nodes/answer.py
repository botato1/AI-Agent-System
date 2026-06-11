from backend.schemas.agent_schema import AgentState
from backend.services.ollama_service import ollama_service


# LangGraph에서 최종 답변 생성을 담당하는 노드
def answer_node(state: AgentState) -> AgentState:
    user_message = state.get("user_message", "")
    question_type = state.get("question_type", "general")

    rag_context = state.get("rag_context") or ""
    memory_context = state.get("memory_context") or ""
    tasks = state.get("tasks") or []

    # Notion 저장 요청은 notion_node에서 최종 저장 결과를 만든다.
    if state.get("need_notion_save", False):
        return {
            **state,
            "final_answer": state.get("final_answer") or "Notion 저장 요청을 확인했습니다. 저장을 진행하겠습니다.",
            "current_step": "answer_node",
            "error": state.get("error"),
        }

    # 문서 기반 질문인데 검색 결과가 없으면 추측 답변 방지
    if state.get("need_rag", False) and not rag_context.strip():
        return {
            **state,
            "final_answer": "요청하신 문서에서 관련 내용을 찾지 못했습니다. 문서가 업로드되어 있는지, 파일명이나 질문 내용을 확인해 주세요.",
            "current_step": "answer_node",
            "error": state.get("error"),
        }

    try:
        final_answer = ollama_service.generate_answer_for_graph(
            user_message=user_message,
            question_type=question_type,
            rag_context=rag_context,
            memory_context=memory_context,
            tasks=tasks,
        )

        return {
            **state,
            "final_answer": final_answer,
            "current_step": "answer_node",
            "error": state.get("error"),
        }

    except Exception as e:
        return {
            **state,
            "final_answer": "답변 생성 중 오류가 발생했습니다.",
            "current_step": "answer_node",
            "error": str(e),
        }