import os
import json

from dotenv import load_dotenv
from langchain_ollama import ChatOllama

from backend.schemas.agent_schema import AgentState


load_dotenv()

llm = ChatOllama(
    model="qwen2.5:7b",
    temperature=0,
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
)

# 사용자 메시지를 분석해서 memory, rag, task_extract, notion_save 필요 여부를 판단하는 노드
def classifier_node(state: AgentState) -> AgentState:

    user_message = state.get("user_message", "")

    prompt = f"""
사용자 메시지를 분석해서 아래 항목이 필요한지 판단해줘.
각 항목에 대해 true 또는 false로만 답해줘.

메시지: {user_message}

1. need_memory: 이전 대화 기록이 필요한가? (예: "아까", "이전에", "방금" 같은 표현)
2. need_rag: 저장된 문서 검색이 필요한가? (문서, 회의록, 자료 관련 질문)
3. need_task_extract: 할 일 추출이 필요한가? (업무, 태스크, 일정 관련)
4. need_notion_save: Notion에 저장이 필요한가? (저장, 기록 요청)

JSON 형식으로만 답해줘:
{{"need_memory": true, "need_rag": false, "need_task_extract": false, "need_notion_save": false}}
"""

    try:
        response = llm.invoke(prompt)
        result = json.loads(response.content)

    except Exception as e:
        return {
            **state,
            "question_type": "general",
            "need_memory": False,
            "need_rag": False,
            "need_task_extract": False,
            "need_notion_save": False,
            "current_step": "classifier_node",
            "error": str(e),
        }

    need_memory = result.get("need_memory", False)
    need_rag = result.get("need_rag", False)
    need_task_extract = result.get("need_task_extract", False)
    need_notion_save = result.get("need_notion_save", False)

    question_type = "general"

    if need_task_extract:
        question_type = "task_extract"
    elif need_notion_save:
        question_type = "notion_save"
    elif need_rag:
        question_type = "rag_search"
    elif need_memory:
        question_type = "memory_search"

    return {
        **state,
        "question_type": question_type,
        "need_memory": need_memory,
        "need_rag": need_rag,
        "need_task_extract": need_task_extract,
        "need_notion_save": need_notion_save,
        "current_step": "classifier_node",
        "error": None,
    }