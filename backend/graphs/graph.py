from langgraph.graph import StateGraph, END
from backend.schemas.agent_schema import AgentState
from backend.graphs.nodes import (
    classifier_node,
    memory_node,
    rag_node,
    task_node,
    notion_node,
    answer_node,
)


def should_run_memory(state: AgentState):
    return "memory" if state.get("need_memory") else "skip_memory"

def should_run_rag(state: AgentState):
    return "rag" if state.get("need_rag") else "skip_rag"

def should_run_task(state: AgentState):
    return "task" if state.get("need_task_extract") else "skip_task"

def should_run_notion(state: AgentState):
    return "notion" if state.get("need_notion_save") else "skip_notion"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("classifier", classifier_node)
    graph.add_node("memory", memory_node)
    graph.add_node("rag", rag_node)
    graph.add_node("task", task_node)
    graph.add_node("notion", notion_node)
    graph.add_node("answer", answer_node)

    graph.set_entry_point("classifier")

    graph.add_conditional_edges("classifier", should_run_memory, {
        "memory": "memory",
        "skip_memory": "rag",
    })
    graph.add_conditional_edges("memory", should_run_rag, {
        "rag": "rag",
        "skip_rag": "task",
    })
    graph.add_conditional_edges("rag", should_run_task, {
        "task": "task",
        "skip_task": "answer",
    })
    graph.add_conditional_edges("task", should_run_notion, {
        "notion": "notion",
        "skip_notion": "answer",
    })

    graph.add_edge("notion", "answer")
    graph.add_edge("answer", END)

    return graph.compile()


agent = build_graph()