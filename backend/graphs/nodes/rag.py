import asyncio
from backend.schemas.agent_schema import AgentState
from backend.services.rag_service import rag_service


def rag_node(state: AgentState) -> AgentState:
    user_message = state["user_message"]

    try:
        result = asyncio.run(rag_service.retrieve_relevant_knowledge(
            query=user_message,
            top_k=5
        ))

        if result["status"] == "success" and result["count"] > 0:
            rag_context = "\n\n".join([doc["content"] for doc in result["data"]])
            sources = [{"title": doc["title"], "score": doc["score"]} for doc in result["data"]]
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