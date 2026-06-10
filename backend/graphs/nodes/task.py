import os
import json
import uuid

from dotenv import load_dotenv
from langchain_ollama import ChatOllama

from backend.schemas.agent_schema import AgentState


load_dotenv()

llm = ChatOllama(
    model="qwen2.5:7b",
    temperature=0,
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
)


def task_node(state: AgentState) -> AgentState:
    # 할 일 추출이 필요 없으면 task_node 실행 건너뜀
    if not state.get("need_task_extract", False):
        return {
            **state,
            "tasks": state.get("tasks", []),
            "current_step": "task_node",
            "error": state.get("error"),
        }

    user_message = state.get("user_message", "")
    rag_context = state.get("rag_context", "")
    memory_context = state.get("memory_context", "")

    # 문서/메모리 내용이 없으면 사용자 요청문을 할 일로 오인하지 않도록 중단
    if not rag_context.strip() and not memory_context.strip():
        return {
            **state,
            "tasks": [],
            "current_step": "task_node",
            "error": "task_source_empty",
        }

    prompt = f"""
아래 대화에서 할 일(Task)을 추출해줘.
담당자, 마감일이 있으면 함께 추출해줘.
원문에 없는 내용은 만들지 마.

사용자 요청:
{user_message}

참고 문서:
{rag_context}

이전 대화:
{memory_context}

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

        for task in tasks:
            if not task.get("task_id"):
                task["task_id"] = str(uuid.uuid4())

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