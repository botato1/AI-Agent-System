import os
import json
import re

from dotenv import load_dotenv
from langchain_ollama import ChatOllama

from backend.schemas.agent_schema import AgentState


load_dotenv()

llm = ChatOllama(
    model="qwen2.5:7b",
    temperature=0,
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
)


# 사용자 질문에서 파일명 추출
def extract_filename_from_query(query: str) -> str | None:
    pattern = r"([가-힣a-zA-Z0-9_\-\s]+\.pdf)"
    match = re.search(pattern, query, re.IGNORECASE)

    if match:
        return match.group(1).strip()

    return None


def has_document_keyword(message: str) -> bool:
    document_keywords = [
        "pdf",
        "PDF",
        "문서",
        "보고서",
        "파일",
        "자료",
        "첨부",
        "업로드",
        "에서 찾아",
        "에서 확인",
        "에서 요약",
        "기반으로",
        "참고해서",
    ]

    return any(keyword in message for keyword in document_keywords)


def has_summary_keyword(message: str) -> bool:
    summary_keywords = [
        "요약",
        "정리",
        "핵심",
        "내용 알려",
        "내용 설명",
    ]

    return any(keyword in message for keyword in summary_keywords)


def is_memory_request(message: str) -> bool:
    memory_keywords = [
        "방금 답변",
        "방금 내용",
        "이전 답변",
        "이전 내용",
        "아까 답변",
        "아까 내용",
        "위 내용",
        "이 내용",
        "그 내용",
        "방금",
        "아까",
        "이전에",
    ]

    return any(keyword in message for keyword in memory_keywords)


def is_task_request(message: str) -> bool:
    task_keywords = [
        "할 일",
        "해야 할 일",
        "태스크",
        "task",
        "담당자",
        "마감일",
        "액션아이템",
        "액션 아이템",
        "업무 정리",
        "업무 추출",
        "업무 목록",
    ]

    return any(keyword in message for keyword in task_keywords)


def is_meeting_document_request(message: str) -> bool:
    meeting_document_keywords = [
        "회의록에서",
        "회의 내용에서",
        "회의 자료에서",
        "회의록 기반",
    ]

    return any(keyword in message for keyword in meeting_document_keywords)


# 사용자 메시지를 분석해서 memory, rag, task_extract, notion_save 필요 여부를 판단하는 노드
def classifier_node(state: AgentState) -> AgentState:
    user_message = state.get("user_message", "")

    prompt = f"""
사용자 메시지를 분석해서 아래 값을 JSON으로만 반환해줘.

[question_type 종류]
- document_summary: 문서, PDF, 보고서, 파일, 회의록 등의 전체 내용 요약 또는 정리 요청
- document_question: 업로드된 문서, PDF, 보고서, 파일, 회의록 안에서 특정 내용을 찾거나 설명해달라는 요청
- term_explanation: 일반적인 용어 설명 요청
- task_extract: 할 일, 업무, 태스크, 담당자, 마감일 추출 요청
- notion_save: Notion 저장, 기록, 보관 요청
- memory_search: 이전 대화 기록이 필요한 요청
- general: 위 항목에 해당하지 않는 일반 질문

[need_memory]
이전 대화 기록이 필요하면 true.
예: 아까, 방금, 이전에, 전에 말한, 이 내용, 위 내용, 방금 답변

[need_rag]
업로드된 문서, PDF, 보고서, 파일, 회의록, 자료, 저장된 지식 검색이 필요하면 true.
특정 문서나 자료에서 찾기, 확인, 요약, 정리를 요청하면 true.

[need_task_extract]
할 일, 업무, 태스크, 담당자, 마감일 정리가 필요하면 true.

[need_notion_save]
Notion 저장, 기록, 보관 요청이면 true.

[중요 규칙]
- 여러 항목이 동시에 true가 될 수 있다.
- 문서나 PDF의 내용을 요약해달라는 요청은 document_summary이고 need_rag=true이다.
- 문서나 PDF 안에서 특정 개념, 함수, 항목을 찾아달라는 요청은 document_question이고 need_rag=true이다.
- 일반 용어 설명은 term_explanation이고 need_rag=false이다.
- 회의록이나 문서에서 할 일을 뽑아달라는 요청은 task_extract이고 need_rag=true, need_task_extract=true이다.
- 이전 답변이나 이전 대화 내용을 저장하라는 요청은 need_memory=true, need_notion_save=true이다.
- 회의록에서 할 일을 정리해서 Notion에 저장하라는 요청은 need_rag=true, need_task_extract=true, need_notion_save=true이다.
- 반드시 JSON 형식으로만 답해라.
- 설명 문장은 쓰지 마라.

메시지:
{user_message}

JSON 형식:
{{
  "question_type": "document_summary/document_question/term_explanation/task_extract/notion_save/memory_search/general",
  "need_memory": true/false,
  "need_rag": true/false,
  "need_task_extract": true/false,
  "need_notion_save": true/false
}}
"""

    try:
        response = llm.invoke(prompt)
        result = json.loads(response.content)

    except Exception as e:
        return {
            **state,
            "question_type": "general",
            "need_general_answer": True,
            "need_memory": False,
            "need_rag": False,
            "need_task_extract": False,
            "need_notion_save": False,
            "target_document_id": state.get("target_document_id"),
            "target_filename": state.get("target_filename"),
            "rag_filter": state.get("rag_filter"),
            "current_step": "classifier_node",
            "error": str(e),
        }

    question_type = result.get("question_type", "general")
    need_memory = result.get("need_memory", False)
    need_rag = result.get("need_rag", False)
    need_task_extract = result.get("need_task_extract", False)
    need_notion_save = result.get("need_notion_save", False)

    target_document_id = state.get("target_document_id")
    target_filename = state.get("target_filename") or extract_filename_from_query(user_message)
    rag_filter = state.get("rag_filter")

    memory_request = is_memory_request(user_message)
    task_request = is_task_request(user_message)
    meeting_request = is_meeting_document_request(user_message)
    document_request = has_document_keyword(user_message)
    summary_request = has_summary_keyword(user_message)

    # 1. 프론트에서 선택 문서가 넘어온 경우 document_id 우선
    if target_document_id:
        rag_filter = {"document_id": target_document_id}
        need_rag = True

    # 2. 파일명이 명시된 경우 해당 파일 검색 필터 준비
    elif target_filename:
        rag_filter = {"filename": target_filename}
        need_rag = True

    # 3. task/회의록 할 일 추출 요청은 가장 우선한다.
    # Notion 저장이 같이 있어도 task_extract를 notion_save로 덮으면 안 된다.
    if task_request or meeting_request or need_task_extract:
        question_type = "task_extract"
        need_memory = False
        need_rag = True
        need_task_extract = True

    # 4. 방금/이전/위 내용 요청이면 memory 필요
    if memory_request:
        need_memory = True

    # 5. 문서 관련 요청이면 RAG 필요
    if document_request:
        need_rag = True

        if question_type in {"general", "term_explanation"}:
            question_type = "document_question"

    # 6. 문서 요약/정리 요청이면 document_summary로 보정
    # 단, task_extract 요청은 문서 요약으로 덮지 않는다.
    if (document_request or target_document_id or target_filename) and summary_request and not need_task_extract:
        question_type = "document_summary"
        need_rag = True

    # 7. 방금/이전 내용을 Notion에 저장하는 경우는 memory 기반 저장이다.
    # 이 경우에는 RAG나 task 추출을 타지 않는다.
    if need_notion_save and need_memory and not need_task_extract:
        question_type = "notion_save"
        need_rag = False

    # 8. 단순 Notion 저장 요청
    if need_notion_save and not need_task_extract and not need_rag:
        question_type = "notion_save"

    need_general_answer = not (
        need_rag or need_memory or need_task_extract or need_notion_save
    )

    return {
        **state,
        "question_type": question_type,
        "need_general_answer": need_general_answer,
        "need_memory": need_memory,
        "need_rag": need_rag,
        "need_task_extract": need_task_extract,
        "need_notion_save": need_notion_save,
        "target_document_id": target_document_id,
        "target_filename": target_filename,
        "rag_filter": rag_filter,
        "current_step": "classifier_node",
        "error": None,
    }