from datetime import datetime

from fastapi import APIRouter

from backend.schemas.agent_schema import AgentState
from backend.graphs.agent_graph import agent_graph


router = APIRouter(
    prefix="/api/agent",
    tags=["Agent"]
)


@router.post("/run")
def run_agent(user_message: str, room_id: str = "test_room"):
    """
    LangGraph Agent 흐름을 테스트하는 API

    실제 서비스용 /api/chat과 분리해서,
    AgentState가 graph를 통해 정상적으로 처리되는지 확인한다.
    """

    initial_state: AgentState = {
        "room_id": room_id,
        "user_message": user_message,
        "source": "text",
        "created_at": datetime.now().isoformat(),
        "messages": [],

        "document_json": None,

        "memory_context": None,
        "rag_context": None,
        "sources": [],

        "question_type": "general",
        "need_general_answer": True,
        "need_memory": False,
        "need_rag": False,
        "need_task_extract": False,
        "need_notion_save": False,

        "summary": None,
        "tasks": [],
        "final_answer": None,

        "notion_result": None,
        "graph_data": None,
        "current_step": "agent_router",
        "error": None,
    }

    result_state = agent_graph.invoke(initial_state)

    return {
        "status": "success" if not result_state.get("error") else "error",
        "room_id": result_state.get("room_id"),
        "question_type": result_state.get("question_type"),
        "final_answer": result_state.get("final_answer"),
        "memory_context": result_state.get("memory_context"),
        "rag_context": result_state.get("rag_context"),
        "tasks": result_state.get("tasks", []),
        "sources": result_state.get("sources", []),
        "notion_result": result_state.get("notion_result"),
        "current_step": result_state.get("current_step"),
        "error": result_state.get("error"),
    }