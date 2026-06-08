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

[판단 기준]

1. need_memory
- 이전 대화 기록이 필요하면 true
- 예: "아까", "방금", "이전에", "전에 말한", "이 내용", "위 내용", "방금 답변"
- 특히 "이 내용을 노션에 저장해줘", "방금 답변 노션에 정리해줘"처럼 이전 답변을 저장/정리하라는 요청이면 true

2. need_rag
- 업로드된 문서, PDF, 회의록, 자료, 저장된 지식 검색이 필요하면 true
- 예: "문서에서 찾아줘", "PDF 내용 참고", "회의록 기반", "자료에 따르면", "업로드한 문서에서"
- 사용자가 "회의록 내용을 요약해줘", "문서 요약해줘", "PDF 요약해줘", "업로드한 파일 내용 정리해줘"처럼 업로드된 자료의 내용을 요약/정리해달라고 하면 true
- 일반 상식 질문이면 false


3. need_task_extract
- 할 일, 업무, 태스크, 담당자, 마감일 정리가 필요하면 true
- 예: "해야 할 일 정리해줘", "담당자별 업무 뽑아줘", "회의록에서 task 추출해줘"

4. need_notion_save
- 사용자가 Notion 저장, 기록, 보관을 요청하면 true
- 예: "노션에 저장해줘", "이 내용 기록해줘", "결과 저장해줘", "이 내용을 노션에 정리해줘"

[중요 규칙]
- 여러 항목이 동시에 true가 될 수 있다.
- "이 내용을 노션에 정리해줘"는 need_memory=true, need_notion_save=true이다.
- 반드시 JSON 형식으로만 답해라.
- 설명 문장은 쓰지 마라.

메시지:
{user_message}

JSON 형식:
{{"need_memory": true/false, "need_rag": true/false, "need_task_extract": true/false, "need_notion_save": true/false}}
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