# LangGraph 노드들을 하나의 실행 흐름으로 연결하는 파일
from langgraph.graph import StateGraph, START, END

from backend.schemas.agent_schema import AgentState
from backend.graphs.nodes.classifier import classifier_node
from backend.graphs.nodes.memory import memory_node
from backend.graphs.nodes.rag import rag_node
from backend.graphs.nodes.task import task_node
from backend.graphs.nodes.answer import answer_node
from backend.graphs.nodes.notion import notion_node


def route_after_classifier(state: AgentState) -> str:
    if state.get("need_memory", False):
        return "memory"
    if state.get("need_rag", False):
        return "rag"
    if state.get("need_task_extract", False):
        return "task"
    return "answer"


def route_after_memory(state: AgentState) -> str:
    if state.get("need_rag", False):
        return "rag"
    if state.get("need_task_extract", False):
        return "task"
    return "answer"


def route_after_rag(state: AgentState) -> str:
    if state.get("need_task_extract", False):
        return "task"
    return "answer"


def route_after_answer(state: AgentState) -> str:
    if state.get("need_notion_save", False):
        return "notion"
    return "end"


def build_agent_graph():
    graph = StateGraph(AgentState)

    # 1. 노드 등록
    graph.add_node("classifier", classifier_node)
    graph.add_node("memory", memory_node)
    graph.add_node("rag", rag_node)
    graph.add_node("task", task_node)
    graph.add_node("answer", answer_node)
    graph.add_node("notion", notion_node)

    # 2. 시작
    graph.add_edge(START, "classifier")

    # 3. classifier 이후 필요한 첫 노드로 이동
    graph.add_conditional_edges(
        "classifier",
        route_after_classifier,
        {
            "memory": "memory",
            "rag": "rag",
            "task": "task",
            "answer": "answer",
        }
    )

    # 4. memory 이후 다음 필요 노드로 이동
    graph.add_conditional_edges(
        "memory",
        route_after_memory,
        {
            "rag": "rag",
            "task": "task",
            "answer": "answer",
        }
    )

    # 5. rag 이후 task 필요 여부 판단
    graph.add_conditional_edges(
        "rag",
        route_after_rag,
        {
            "task": "task",
            "answer": "answer",
        }
    )

    # 6. task 이후 answer
    graph.add_edge("task", "answer")

    # 7. answer 이후 notion 필요 여부 판단
    graph.add_conditional_edges(
        "answer",
        route_after_answer,
        {
            "notion": "notion",
            "end": END,
        }
    )

    # 8. notion 이후 종료
    graph.add_edge("notion", END)

    return graph.compile()


agent_graph = build_agent_graph()