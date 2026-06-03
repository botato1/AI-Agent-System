import os
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from backend.schemas.agent_schema import AgentState

load_dotenv()
llm = ChatOllama(model="qwen2.5:7b", temperature=0.7, base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))

def answer_node(state: AgentState) -> AgentState:
    user_message = state["user_message"]
    memory_context = state.get("memory_context", "")
    rag_context = state.get("rag_context", "")
    tasks = state.get("tasks", [])

    prompt = f"""
너는 도비(Doby)라는 AI 비서야.
아래 정보를 참고해서 사용자 질문에 친절하게 답해줘.

사용자 질문: {user_message}

이전 대화 기록:
{memory_context}

참고 문서:
{rag_context}

추출된 할 일 목록:
{tasks}

답변:
"""

    response = llm.invoke(prompt)

    return {
        **state,
        "final_answer": response.content,
        "current_step": "done",
    }