from backend.schemas.agent_schema import AgentState
from backend.services.ollama_service import ollama_service
from backend.db.crud import save_tasks


# LangGraph에서 회의록/문서 기반 할 일 추출을 담당하는 노드
def task_node(state: AgentState) -> AgentState:
    # 할 일 추출이 필요 없으면 task_node 실행 건너뜀
    if not state.get("need_task_extract", False):
        return {
            **state,
            "tasks": state.get("tasks") or [],
            "current_step": "task_node",
            "error": state.get("error"),
        }

    rag_context = state.get("rag_context") or ""
    memory_context = state.get("memory_context") or ""
    document_json = state.get("document_json") or {}

    # 문서/음성 JSON이 직접 들어온 경우 우선 사용
    if document_json.get("content"):
        source_content = document_json.get("content")

    # RAG 검색 결과가 있으면 RAG context 사용
    elif rag_context.strip():
        source_content = rag_context

    # 이전 대화 기반 task 추출이 필요한 경우 memory 사용
    elif memory_context.strip():
        source_content = memory_context

    else:
        # 사용자 요청문만 보고 task를 만들지 않도록 방어
        return {
            **state,
            "tasks": [],
            "current_step": "task_node",
            "error": "task_source_empty",
        }

    try:
        tasks = ollama_service.extract_tasks_from_content(source_content)

        room_id = state.get("room_id") or ""

        document_id = (
            state.get("target_document_id")
            or document_json.get("id")
            or document_json.get("chroma_id")
            or state.get("target_filename")
            or "unknown_document"
        )

        # 추출된 할 일이 있으면 tasks 테이블에 저장
        if tasks:
            save_tasks(
                tasks=tasks,
                document_id=document_id,
                conversation_id=room_id,
            )

        return {
            **state,
            "tasks": tasks,
            "current_step": "task_node",
            "error": None,
        }

    except Exception as e:
        print(f"[task_node 에러]: {str(e)}")

        return {
            **state,
            "tasks": [],
            "current_step": "task_node",
            "error": str(e),
        }