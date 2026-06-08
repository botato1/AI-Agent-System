import os
import json
import uuid
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from backend.schemas.agent_schema import AgentState

load_dotenv()
llm = ChatOllama(model="qwen2.5:7b", temperature=0, base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))

def task_node(state: AgentState) -> AgentState:
    user_message = state.get("user_message", "")
    rag_context = state.get("rag_context", "")
    memory_context = state.get("memory_context", "")

    prompt = f"""
아래 대화에서 할 일(Task)을 추출해줘.
담당자, 마감일이 있으면 함께 추출해줘.

대화 내용: {user_message}
참고 문서: {rag_context}
이전 대화: {memory_context}

JSON 형식으로만 답해줘:
{{
  "tasks": [
    {{
      "task_id": "고유ID(uuid)",
      "task": "할 일 내용",
      "assignee": "담당자 또는 null",
      "deadline": "마감일 또는 null",
      "status": "todo"
    }}
  ]
}}
"""

    try:
        response = llm.invoke(prompt)
        result = json.loads(response.content)

        tasks = result.get("tasks", [])

        for t in tasks:
            if not t.get("task_id"):
                t["task_id"] = str(uuid.uuid4())
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