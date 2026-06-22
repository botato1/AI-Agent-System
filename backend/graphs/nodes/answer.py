from backend.schemas.agent_schema import AgentState
from backend.services.ollama_service import ollama_service


# LangGraph에서 최종 답변 생성을 담당하는 노드
def answer_node(state: AgentState) -> AgentState:
    user_message = state.get("user_message", "")
    question_type = state.get("question_type", "general_answer")

    rag_context = state.get("rag_context") or ""
    memory_context = state.get("memory_context") or ""
    tasks = state.get("tasks") or []

    # rag_node에서 저장한 RAG 검색 결과
    retrieved_docs = state.get("retrieved_docs") or []
    low_confidence = state.get("low_confidence", False)

    # Notion 저장 요청은 notion_node에서 최종 저장 결과를 만든다.
    if state.get("need_notion_save", False):
        return {
            **state,
            "final_answer": state.get("final_answer") or "Notion 저장 요청을 확인했습니다. 저장을 진행하겠습니다.",
            "current_step": "answer_node",
            "error": state.get("error"),
        }

    # RAG 검색이 필요한 질문인데 검색 결과가 없으면 추측 답변 방지
    if state.get("need_rag", False) and not rag_context.strip():
        return {
            **state,
            "final_answer": "관련 문서 또는 지식 검색 결과를 찾지 못했습니다. 질문 내용을 조금 더 구체적으로 입력해 주세요.",
            "current_step": "answer_node",
            "error": state.get("error"),
        }

    # 할 일 추출 결과가 이미 있으면 LLM에게 다시 답변 생성을 맡기지 않고,
    # 추출된 tasks 배열을 기준으로 최종 답변을 구성한다.
    if state.get("need_task_extract", False) and tasks:
        task_lines = []

        for idx, task in enumerate(tasks, start=1):
            task_title = (
                task.get("task")
                or task.get("title")
                or task.get("content")
                or "할 일 없음"
            )
            assignee = task.get("assignee") or "담당자 미정"
            deadline = task.get("deadline") or "마감일 미정"

            task_lines.append(
                f"{idx}. {task_title}\n"
                f"   - 담당자: {assignee}\n"
                f"   - 마감일: {deadline}"
            )

        if question_type == "task_from_memory":
            answer_title = "대화에서 추출한 할 일은 다음과 같습니다."
        else:
            answer_title = "문서에서 추출한 할 일은 다음과 같습니다."

        final_answer = answer_title + "\n\n" + "\n\n".join(task_lines)

        return {
            **state,
            "final_answer": final_answer,
            "current_step": "answer_node",
            "error": state.get("error"),
        }

    # 할 일 추출 요청이었지만 tasks가 비어 있는 경우
    if state.get("need_task_extract", False) and not tasks:
        return {
            **state,
            "final_answer": "문서 또는 대화 내용에서 추출할 수 있는 할 일을 찾지 못했습니다.",
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
            retrieved_docs=retrieved_docs,
            low_confidence=low_confidence,
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