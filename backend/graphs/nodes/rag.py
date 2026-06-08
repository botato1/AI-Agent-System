import asyncio
from backend.schemas.agent_schema import AgentState
from backend.services.rag_service import rag_service


def rag_node(state: AgentState) -> AgentState:
    if not state.get("need_rag", False):
        return {
            **state,
            "rag_context": state.get("rag_context") or "",
            "sources": state.get("sources", []),
            "current_step": "rag_node",
            "error": None,
        }
    user_message = state.get("user_message", "")

    try:
        result = asyncio.run(rag_service.retrieve_relevant_knowledge(
            query=user_message,
            top_k=5
        ))

        if result.get("status") == "success" and result.get("count", 0) > 0:
            rag_context = "\n\n".join([
                doc.get("content", "")
                for doc in result.get("data", [])
            ])
            
            sources = [
                {
                    "title": doc.get("title"),
                    "score": doc.get("score")
                }
                for doc in result.get("data", [])
            ]
        else:
            rag_context = ""
            sources = []

    except Exception as e:
        print(f"[rag_node 에러]: {str(e)}")
        rag_context = ""
        sources = []

    return {
        **state,
        "rag_context": rag_context,
        "sources": sources,
    }