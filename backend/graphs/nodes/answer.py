import os

from dotenv import load_dotenv
from langchain_ollama import ChatOllama

from backend.schemas.agent_schema import AgentState


load_dotenv()

llm = ChatOllama(
    model="qwen2.5:7b",
    temperature=0.7,
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
)


DOBY_SYSTEM_GUIDE = """
너는 도비(Doby)라는 IT 프로젝트 업무 지원 AI 비서야.

[주요 역할]
- 업로드된 문서, PDF, 회의록, 개발 자료를 요약하고 설명한다.
- 문서 기반 질문에 답변한다.
- 회의록에서 담당자, 할 일, 마감일을 정리한다.
- 개인 일정이나 업무 일정을 정리하고 관리할 수 있도록 돕는다.
- 이전 답변이나 분석 결과를 Notion 저장 흐름과 연결한다.
- 개발자, IT 직무 종사자, 프로젝트 팀원이 업무를 정리할 수 있도록 돕는다.

[제한 사항]
- 날씨, 뉴스, 주식, 실시간 검색처럼 현재 시스템에서 지원하지 않는 기능을 할 수 있다고 말하지 않는다.
- 지원하지 않는 기능을 물으면 불가능하다고만 끝내지 말고, 이 서비스에서 가능한 IT 문서/회의록/일정/업무 정리 기능을 안내한다.
- 참고 문서가 필요한 질문인데 참고 문서가 없으면 추측하지 않는다.
- 답변은 한국어로 작성한다.
"""


def answer_node(state: AgentState) -> AgentState:
    user_message = state.get("user_message", "")
    question_type = state.get("question_type", "general")

    need_rag = state.get("need_rag", False)
    rag_context = state.get("rag_context") or ""

    need_memory = state.get("need_memory", False)
    memory_context = state.get("memory_context") or ""

    tasks = state.get("tasks", [])

    # Notion 저장 요청은 notion_node에서 최종 저장 결과를 만든다.
    # 여기서 LLM에게 "노션에 저장해줘"를 답변 생성시키면
    # "저장 기능이 없습니다" 같은 잘못된 답변이 나올 수 있다.
    if state.get("need_notion_save", False):
        return {
            **state,
            "final_answer": state.get("final_answer") or "Notion 저장 요청을 확인했습니다. 저장을 진행하겠습니다.",
            "current_step": "answer_node",
            "error": state.get("error"),
        }

    # 문서 기반 질문인데 검색 결과가 없으면 추측 답변 방지
    if need_rag and not rag_context.strip():
        return {
            **state,
            "final_answer": "요청하신 문서에서 관련 내용을 찾지 못했습니다. 문서가 업로드되어 있는지, 파일명이나 질문 내용을 확인해 주세요.",
            "current_step": "answer_node",
            "error": state.get("error"),
        }

    if question_type == "document_summary":
        prompt = f"""
{DOBY_SYSTEM_GUIDE}

아래 참고 문서 내용만 사용해서 사용자가 요청한 문서를 요약해줘.

[규칙]
- 참고 문서에 없는 내용은 추측하지 마라.
- 참고 문서 내용만 근거로 답해라.
- 핵심 내용, 주요 근거, 결론 순서로 정리해라.
- 답변은 한국어로 작성해라.

사용자 질문:
{user_message}

참고 문서:
{rag_context}

답변:
"""

    elif need_rag:
        prompt = f"""
{DOBY_SYSTEM_GUIDE}

아래 참고 문서 내용만 사용해서 사용자 질문에 답해줘.

[규칙]
- 참고 문서에 있는 내용만 근거로 답해라.
- 참고 문서에 없는 내용은 모른다고 답해라.
- 문서 기반 답변임을 자연스럽게 밝혀라.
- 답변은 한국어로 작성해라.

사용자 질문:
{user_message}

참고 문서:
{rag_context}

답변:
"""

    elif tasks:
        prompt = f"""
{DOBY_SYSTEM_GUIDE}

아래 추출된 할 일 목록을 보기 좋게 정리해줘.

[규칙]
- 담당자, 할 일, 마감일이 있으면 구분해서 정리해라.
- 없는 정보는 임의로 만들지 마라.
- 답변은 한국어로 작성해라.

사용자 질문:
{user_message}

할 일 목록:
{tasks}

답변:
"""

    elif need_memory:
        prompt = f"""
{DOBY_SYSTEM_GUIDE}

아래 이전 대화 기록을 참고해서 사용자 요청에 답해줘.

[규칙]
- 이전 대화 기록에 있는 내용만 근거로 답해라.
- 이전 대화 기록에 없는 내용은 임의로 만들지 마라.
- 답변은 한국어로 작성해라.

사용자 질문:
{user_message}

이전 대화 기록:
{memory_context}

답변:
"""

    else:
        prompt = f"""
{DOBY_SYSTEM_GUIDE}

사용자 질문에 답해줘.

[규칙]
- 도비가 할 수 있는 일은 IT 프로젝트 업무 지원, 문서 요약, 회의록 정리, 문서 기반 질의응답, 할 일 추출, 개인/업무 일정 정리, Notion 저장 보조이다.
- 날씨, 뉴스, 주식, 실시간 검색 같은 기능을 할 수 있다고 말하지 마라.
- 사용자가 "너는 뭘 할 수 있어?"라고 물으면 IT 문서/회의록/개발 업무/일정 정리 기능 중심으로 답해라.
- 답변은 한국어로 작성해라.

사용자 질문:
{user_message}

답변:
"""

    try:
        response = llm.invoke(prompt)

        return {
            **state,
            "final_answer": response.content,
            "current_step": "answer_node",
            "error": state.get("error"),
        }

    except Exception as e:
        return {
            **state,
            "final_answer": "답변 생성 중 오류가 발생했습니다.",
            "current_step": "answer_node",
            "error": str(e),
        }