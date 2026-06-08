# LangGraph 노드들을 하나의 실행 흐름으로 연결하는 파일
from langgraph.graph import StateGraph, START, END

from backend.schemas.agent_schema import AgentState
from backend.graphs.nodes.classifier import classifier_node
from backend.graphs.nodes.memory import memory_node
from backend.graphs.nodes.rag import rag_node
from backend.graphs.nodes.task import task_node
from backend.graphs.nodes.answer import answer_node
from backend.graphs.nodes.notion import notion_node

# LangGraph Agent 실행 흐름을 구성하는 함수
def build_agent_graph():
    graph = StateGraph(AgentState)

    # 1. 노드 등록
    graph.add_node("classifier", classifier_node)
    graph.add_node("memory", memory_node)
    graph.add_node("rag", rag_node)
    graph.add_node("task", task_node)
    graph.add_node("answer", answer_node)
    graph.add_node("notion", notion_node)

    # 2. 실행 순서 연결
    graph.add_edge(START, "classifier")
    graph.add_edge("classifier", "memory")
    graph.add_edge("memory", "rag")
    graph.add_edge("rag", "task")
    graph.add_edge("task", "answer")
    graph.add_edge("answer", "notion")
    graph.add_edge("notion", END)

    # 3. 그래프 컴파일
    return graph.compile()


agent_graph = build_agent_graph()