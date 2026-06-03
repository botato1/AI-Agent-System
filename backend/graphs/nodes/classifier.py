import os
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from backend.schemas.agent_schema import AgentState

load_dotenv()
llm = ChatOllama(model="qwen2.5:7b", temperature=0, base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))

def classifier_node(state: AgentState) -> AgentState:
    user_message = state["user_message"]

    prompt = f"""
사용자 메시지를 분석해서 아래 항목이 필요한지 판단해줘.
각 항목에 대해 true 또는 false로만 답해줘.

메시지: {user_message}

1. need_memory: 이전 대화 기록이 필요한가? (예: "아까", "이전에", "방금" 같은 표현)
2. need_rag: 저장된 문서 검색이 필요한가? (문서, 회의록, 자료 관련 질문)
3. need_task_extract: 할 일 추출이 필요한가? (업무, 태스크, 일정 관련)
4. need_notion_save: Notion에 저장이 필요한가? (저장, 기록 요청)

JSON 형식으로만 답해줘:
{{"need_memory": true/false, "need_rag": true/false, "need_task_extract": true/false, "need_notion_save": true/false}}
"""

    response = llm.invoke(prompt)
    
    import json
    try:
        result = json.loads(response.content)
    except:
        result = {
            "need_memory": False,
            "need_rag": False,
            "need_task_extract": False,
            "need_notion_save": False
        }

    return {
        **state,
        "question_type": "general",
        "need_memory": result.get("need_memory", False),
        "need_rag": result.get("need_rag", False),
        "need_task_extract": result.get("need_task_extract", False),
        "need_notion_save": result.get("need_notion_save", False),
    }