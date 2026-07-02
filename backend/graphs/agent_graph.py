from langgraph.graph import StateGraph, START, END

from backend.schemas.agent_schema import AgentState
from backend.graphs.nodes.classifier import classifier_node
from backend.graphs.nodes.memory import memory_node
from backend.graphs.nodes.rag import rag_node
from backend.graphs.nodes.task import task_node
from backend.graphs.nodes.answer import answer_node


def route_after_classifier(state: AgentState) -> str:
    question_type = state.get("question_type", "general_answer")

    if question_type == "task_from_memory":
        return "memory"

    if question_type in {"task_from_rag", "knowledge_search", "summary_from_rag"}:
        return "rag"

    return "answer"


def route_after_memory(state: AgentState) -> str:
    question_type = state.get("question_type", "general_answer")

    if question_type == "task_from_memory":
        return "task"

    return "answer"


def route_after_rag(state: AgentState) -> str:
    question_type = state.get("question_type", "general_answer")

    if question_type == "task_from_rag":
        return "task"

    return "answer"


def route_after_answer(state: AgentState) -> str:
    return "end"


def build_agent_graph():
    graph = StateGraph(AgentState)

    graph.add_node("classifier", classifier_node)
    graph.add_node("memory", memory_node)
    graph.add_node("rag", rag_node)
    graph.add_node("task", task_node)
    graph.add_node("answer", answer_node)

    graph.add_edge(START, "classifier")

    graph.add_conditional_edges(
        "classifier",
        route_after_classifier,
        {
            "memory": "memory",
            "rag": "rag",
            "answer": "answer",
        },
    )

    graph.add_conditional_edges(
        "memory",
        route_after_memory,
        {
            "task": "task",
            "answer": "answer",
        },
    )

    graph.add_conditional_edges(
        "rag",
        route_after_rag,
        {
            "task": "task",
            "answer": "answer",
        },
    )

    graph.add_edge("task", "answer")

    graph.add_conditional_edges(
        "answer",
        route_after_answer,
        {
            "end": END,
        },
    )


    return graph.compile()


agent_graph = build_agent_graph()