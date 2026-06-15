from backend.schemas.agent_schema import AgentState
from backend.services.ollama_service import ollama_service


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
        # 회의록/문서/메모리 내용에서 할 일 추출
        tasks = ollama_service.extract_tasks_from_content(source_content)

        # 로그인 기능이 없는 현재 구조에서는 현재 사용자를 식별할 수 없으므로
        # 추출된 전체 담당자 업무를 자동 저장하지 않는다.
        # 실제 저장은 사용자가 선택한 업무만 POST /api/tasks로 처리한다.
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