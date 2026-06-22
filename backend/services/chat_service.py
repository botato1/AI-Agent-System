import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from backend.schemas.chat_schema import ChatRequest
from backend.schemas.response_schema import ChatResponseSchema
from backend.schemas.agent_schema import AgentState
from backend.db.crud import (
    insert_message,
    get_messages,
    get_latest_document_by_conversation,
    get_document_by_filename_and_conversation,
)
from backend.graphs.agent_graph import agent_graph


# 사용자가 특정 문서/파일/음성/회의록을 가리키는 질문인지 확인하는 함수
def is_document_reference_message(message: str) -> bool:
    if not message:
        return False

    keywords = [
        "이 문서", "이 파일", "이 자료", "이 회의록", "이 음성",
        "방금 올린", "방금 업로드", "첨부한", "업로드한",
        "문서에서", "파일에서", "자료에서", "회의록에서", "음성에서",
        "해당 문서", "해당 파일", "해당 자료", "해당 회의록", "해당 음성",
    ]

    return any(keyword in message for keyword in keywords)


# DB에서 가져온 메시지를 AgentState에서 쓰기 좋은 dict 리스트로 정리
def normalize_messages_for_state(messages: list | None) -> list[dict]:
    if not messages:
        return []

    normalized_messages = []

    for message in messages:
        # 이미 dict 형태인 경우
        if isinstance(message, dict):
            normalized_messages.append({
                "role": message.get("role"),
                "content": message.get("content"),
                "created_at": message.get("created_at"),
            })

        # sqlite3.Row 같은 객체인 경우
        else:
            try:
                normalized_messages.append({
                    "role": message["role"],
                    "content": message["content"],
                    "created_at": message["created_at"] if "created_at" in message.keys() else None,
                })
            except Exception:
                continue

    return normalized_messages


# ChatRequest를 LangGraph에서 사용할 AgentState로 변환하는 함수
def create_initial_state(
    request: ChatRequest,
    messages: list | None = None
) -> AgentState:
    # 1. 프론트에서 넘어온 문서 정보
    target_document_id = request.target_document_id
    target_filename = request.target_filename

    # 2. target_document_id는 없고 target_filename만 있는 경우
    #    room_id + filename으로 documents 테이블에서 document_id를 찾는다.
    if not target_document_id and target_filename:
        matched_document = get_document_by_filename_and_conversation(
            request.room_id,
            target_filename
        )

        if matched_document:
            target_document_id = matched_document.get("id")
            target_filename = matched_document.get("title")

    # 3. target_document_id와 target_filename이 둘 다 없는 경우
    #    사용자가 특정 문서/파일/음성/회의록을 가리킬 때만 최근 업로드 문서를 자동 연결한다.
    #    일반 지식 검색 질문이 최근 문서 필터에 묶이는 문제를 방지한다.
    if (
        not target_document_id
        and not target_filename
        and is_document_reference_message(request.content)
    ):
        latest_document = get_latest_document_by_conversation(request.room_id)

        if latest_document:
            target_document_id = latest_document.get("id")
            target_filename = latest_document.get("title")

    # 4. RAG 검색 필터 생성
    #    document_id가 있으면 document_id 우선 사용
    #    document_id가 없고 filename만 있으면 filename 사용
    if target_document_id:
        rag_filter = {"document_id": target_document_id}
    elif target_filename:
        rag_filter = {"filename": target_filename}
    else:
        rag_filter = None

    return {
        # 1. 채팅 기본 정보
        "room_id": request.room_id,
        "user_message": request.content,
        "source": request.source,
        "created_at": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(),

        # 이전 대화 기록
        # "방금 추출한 할 일 목록을 노션에 저장해줘" 같은 요청에서
        # notion_node가 직전 assistant 답변을 찾기 위해 사용한다.
        "messages": normalize_messages_for_state(messages),

        # 2. 문서 / STT / 파일 처리 결과
        "document_json": None,

        # 3. 이전 대화 / RAG 검색 결과
        "memory_context": None,
        "rag_context": None,

        # rag_service.retrieve_relevant_knowledge() 반환값 전체
        # answer_node → ollama_client.generate_answer_for_graph()의
        # rag_search_result 인자로 전달된다.
        "rag_search_result": None,

        # 프론트 응답 / graph_data 표시용으로 유지
        "retrieved_docs": [],
        "low_confidence": False,
        "sources": [],

        # 프론트에서 선택한 문서 검색용 필드
        # 프론트가 document_id를 안 보내도 filename 또는 문서 지시어 기준으로 자동 보완됨
        "target_document_id": target_document_id,
        "target_filename": target_filename,
        "rag_filter": rag_filter,

        # 4. 질문 유형 판단 결과
        "question_type": "general_answer",
        "need_general_answer": True,
        "need_memory": False,
        "need_rag": False,
        "need_task_extract": False,
        "need_notion_save": False,

        # 5. LLM / 업무 추출 결과
        "summary": None,
        "tasks": [],
        "final_answer": None,
        "save_target_content": None,

        # 6. Notion / Graph / 오류 결과
        "notion_result": None,
        "graph_data": None,
        "current_step": "chat_service",
        "error": None,
    }


def normalize_sources(sources: list | None) -> list[dict]:
    """
    sources가 문자열 리스트 또는 dict 리스트로 들어와도
    ChatResponseSchema의 SourceSchema 형식에 맞게 변환한다.
    """
    if not sources:
        return []

    normalized_sources = []

    for idx, source in enumerate(sources):
        if isinstance(source, dict):
            normalized_sources.append({
                "id": source.get("id")
                    or source.get("document_id")
                    or source.get("chroma_id")
                    or f"source_{idx + 1}",
                "source": source.get("source")
                    or source.get("filename")
                    or source.get("title")
                    or "unknown",
                "title": source.get("title")
                    or source.get("filename")
                    or source.get("source")
                    or f"source_{idx + 1}",
                "score": source.get("score"),
            })

        elif isinstance(source, str):
            normalized_sources.append({
                "id": f"source_{idx + 1}",
                "source": source,
                "title": source,
                "score": None,
            })

    return normalized_sources


def normalize_task_status(status: str | None) -> str:
    """
    LLM이 한글 상태값을 반환해도
    ChatResponseSchema에서 허용하는 status 값으로 변환한다.

    허용값:
    todo / in_progress / done / delayed
    """
    if not status:
        return "todo"

    status = str(status).strip()

    status_map = {
        "todo": "todo",
        "할일": "todo",
        "할 일": "todo",
        "대기": "todo",
        "예정": "todo",
        "미완료": "todo",
        "해야함": "todo",
        "해야 함": "todo",

        "in_progress": "in_progress",
        "doing": "in_progress",
        "진행중": "in_progress",
        "진행 중": "in_progress",
        "진행": "in_progress",
        "작업중": "in_progress",
        "작업 중": "in_progress",

        "done": "done",
        "완료": "done",
        "끝남": "done",
        "완료됨": "done",
        "처리완료": "done",
        "처리 완료": "done",

        "delayed": "delayed",
        "지연": "delayed",
        "연기": "delayed",
        "늦어짐": "delayed",
        "보류": "delayed",
    }

    return status_map.get(status, "todo")


def normalize_task_priority(priority: str | None) -> str:
    """
    LLM이 한글 우선순위 값을 반환해도
    스키마에서 허용하는 priority 값으로 변환한다.

    허용값:
    high / medium / low
    """
    if not priority:
        return "medium"

    priority = str(priority).strip()

    priority_map = {
        "high": "high",
        "높음": "high",
        "상": "high",
        "긴급": "high",
        "중요": "high",

        "medium": "medium",
        "보통": "medium",
        "중간": "medium",
        "중": "medium",
        "일반": "medium",

        "low": "low",
        "낮음": "low",
        "하": "low",
        "여유": "low",
    }

    return priority_map.get(priority, "medium")


# LLM이 한국어 조사까지 담당자 이름으로 추출한 경우 보정한다.
def normalize_assignee_name(assignee: str | None) -> str | None:
    if not assignee:
        return None

    assignee = str(assignee).strip()

    if not assignee:
        return None

    # 여러 명이 문자열로 들어오는 경우는 그대로 둔다.
    if "," in assignee or "/" in assignee or " " in assignee:
        return assignee

    # 이름 뒤에 붙은 '이'를 제거
    # 너무 짧은 이름은 건드리지 않음
    if assignee.endswith("이") and len(assignee) >= 3:
        assignee = assignee[:-1]

    return assignee


def normalize_tasks(tasks: list | None) -> list[dict]:
    """
    LLM 또는 task_extract_node에서 나온 tasks를
    ChatResponseSchema 형식에 맞게 정리한다.

    특히 status가 '진행중', '완료', '대기'처럼 한글로 들어오면
    Pydantic Literal 검증에서 500 에러가 나기 때문에
    응답 생성 전에 영어 enum 값으로 변환한다.
    """
    if not tasks:
        return []

    normalized_tasks = []

    for idx, task in enumerate(tasks):
        if not isinstance(task, dict):
            continue

        normalized_tasks.append({
            "task_id": task.get("task_id")
                or task.get("id")
                or f"task_{idx + 1}",
            "task": task.get("task")
                or task.get("title")
                or task.get("content")
                or "",
            "assignee": normalize_assignee_name(task.get("assignee")),
            "deadline": task.get("deadline")
                or task.get("due_date")
                or task.get("due"),
            "status": normalize_task_status(task.get("status")),
            "priority": normalize_task_priority(task.get("priority")),
            "room_id": task.get("room_id")
                or task.get("conversation_id"),
            "document_id": task.get("document_id"),
            "created_at": task.get("created_at"),
        })

    return normalized_tasks


# AgentState를 프론트 응답 형식으로 반환하는 함수
def build_chat_response(state: AgentState) -> ChatResponseSchema:
    raw_sources = state.get("sources", [])
    sources = normalize_sources(raw_sources)

    raw_tasks = state.get("tasks", [])
    tasks = normalize_tasks(raw_tasks)

    retrieved_docs = state.get("retrieved_docs") or []

    return ChatResponseSchema(
        room_id=state.get("room_id", ""),
        answer=state.get("final_answer") or "",
        summary=state.get("summary"),
        tasks=tasks,
        sources=sources,
        notion_result=state.get("notion_result"),
        graph_data={
            "current_step": state.get("current_step"),
            "question_type": state.get("question_type"),
            "need_general_answer": state.get("need_general_answer"),
            "need_memory": state.get("need_memory"),
            "need_rag": state.get("need_rag"),
            "need_task_extract": state.get("need_task_extract"),
            "need_notion_save": state.get("need_notion_save"),
            "target_document_id": state.get("target_document_id"),
            "target_filename": state.get("target_filename"),
            "rag_filter": state.get("rag_filter"),
            "low_confidence": state.get("low_confidence"),
            "retrieved_docs_count": len(retrieved_docs),
        },
        error=state.get("error"),
    )


# AgentState를 LangGraph에 전달해서 실행하는 함수
def run_agent_graph(state: AgentState) -> AgentState:
    return agent_graph.invoke(state)


async def handle_chat(request: ChatRequest) -> ChatResponseSchema:
    # 1. 사용자 메시지 DB 저장
    insert_message(
        conversation_id=request.room_id,
        role="user",
        content=request.content
    )

    # 2. 현재 채팅방의 대화 기록 조회
    # 방금 저장한 user 메시지와 이전 assistant 답변이 함께 들어온다.
    messages = get_messages(request.room_id)

    # 3. ChatRequest를 AgentState로 변환
    state = create_initial_state(request, messages=messages)

    # 4. LangGraph 실행
    # FastAPI async event loop와 그래프 내부 동기 작업 충돌 방지
    result_state = await asyncio.to_thread(run_agent_graph, state)

    # 5. 최종 답변 추출
    answer = result_state.get("final_answer") or "응답을 생성하지 못했습니다."

    # 6. assistant 답변 DB 저장
    insert_message(
        conversation_id=request.room_id,
        role="assistant",
        content=answer
    )

    # 7. 최종 응답 반환
    return build_chat_response(result_state)