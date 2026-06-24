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


# 상수
DOCUMENT_REFERENCE_KEYWORDS = [
    "이 문서", "이 파일", "이 자료", "이 회의록", "이 음성",
    "방금 올린", "방금 업로드", "첨부한", "업로드한",
    "문서에서", "파일에서", "자료에서", "회의록에서", "음성에서",
    "해당 문서", "해당 파일", "해당 자료", "해당 회의록", "해당 음성",
]

STATUS_MAP = {
    "todo": "todo", "할일": "todo", "할 일": "todo",
    "대기": "todo", "예정": "todo", "미완료": "todo",
    "해야함": "todo", "해야 함": "todo",
    "in_progress": "in_progress", "doing": "in_progress",
    "진행중": "in_progress", "진행 중": "in_progress",
    "진행": "in_progress", "작업중": "in_progress", "작업 중": "in_progress",
    "done": "done", "완료": "done", "끝남": "done",
    "완료됨": "done", "처리완료": "done", "처리 완료": "done",
    "delayed": "delayed", "지연": "delayed", "연기": "delayed",
    "늦어짐": "delayed", "보류": "delayed",
}

PRIORITY_MAP = {
    "high": "high", "높음": "high", "상": "high", "긴급": "high", "중요": "high",
    "medium": "medium", "보통": "medium", "중간": "medium", "중": "medium", "일반": "medium",
    "low": "low", "낮음": "low", "하": "low", "여유": "low",
}

# 헬퍼 함수
# 사용자가 특정 문서/파일/음성/회의록을 가리키는 질문인지 확인
def is_document_reference_message(message: str) -> bool:
    if not message:
        return False

    return any(keyword in message for keyword in DOCUMENT_REFERENCE_KEYWORDS)

# numpy 타입을 Python 기본 타입으로 변환
def to_json_safe(value):
    try:
        import numpy as np

        if isinstance(value, np.bool_):
            return bool(value)
        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, np.floating):
            return float(value)
        if isinstance(value, np.ndarray):
            return value.tolist()

    except ImportError:
        pass

    if isinstance(value, dict):
        return {key: to_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json_safe(item) for item in value]

    return value

# DB에서 가져온 메시지를 AgentState용 dict 리스트로 변환
def normalize_messages_for_state(messages: list | None) -> list[dict]:
    if not messages:
        return []

    normalized = []

    for message in messages:
        if isinstance(message, dict):
            normalized.append({
                "role": message.get("role"),
                "content": message.get("content"),
                "created_at": message.get("created_at"),
            })
        else:
            try:
                normalized.append({
                    "role": message["role"],
                    "content": message["content"],
                    "created_at": message["created_at"] if "created_at" in message.keys() else None,
                })
            except Exception:
                continue

    return normalized

# 한글 상태값을 ChatResponseSchema 허용값으로 변환
def normalize_task_status(status: str | None) -> str:
    if not status:
        return "todo"

    return STATUS_MAP.get(str(status).strip(), "todo")

# 한글 우선순위값을 ChatResponseSchema 허용값으로 변환
def normalize_task_priority(priority: str | None) -> str:
    if not priority:
        return "medium"

    return PRIORITY_MAP.get(str(priority).strip(), "medium")

# LLM이 한국어 조사까지 담당자 이름으로 추출한 경우 보정
def normalize_assignee_name(assignee: str | None) -> str | None:
    if not assignee:
        return None

    assignee = str(assignee).strip()

    if not assignee:
        return None

    if "," in assignee or "/" in assignee or " " in assignee:
        return assignee

    if assignee.endswith("이") and len(assignee) >= 3:
        assignee = assignee[:-1]

    return assignee

# sources를 ChatResponseSchema의 SourceSchema 형식으로 변환
def normalize_sources(sources: list | None) -> list[dict]:
    if not sources:
        return []

    normalized = []

    for idx, source in enumerate(sources):
        if isinstance(source, dict):
            normalized.append({
                "id": source.get("id") or source.get("document_id") or source.get("chroma_id") or f"source_{idx + 1}",
                "source": source.get("source") or source.get("filename") or source.get("title") or "unknown",
                "title": source.get("title") or source.get("filename") or source.get("source") or f"source_{idx + 1}",
                "score": to_json_safe(source.get("score")),
            })
        elif isinstance(source, str):
            normalized.append({
                "id": f"source_{idx + 1}",
                "source": source,
                "title": source,
                "score": None,
            })

    return normalized

# tasks를 ChatResponseSchema 형식으로 변환하고 한글 status/priority를 영어로 변환
def normalize_tasks(tasks: list | None) -> list[dict]:
    if not tasks:
        return []

    normalized = []

    for idx, task in enumerate(tasks):
        if not isinstance(task, dict):
            continue

        normalized.append({
            "task_id": task.get("task_id") or task.get("id") or f"task_{idx + 1}",
            "task": task.get("task") or task.get("title") or task.get("content") or "",
            "assignee": normalize_assignee_name(task.get("assignee")),
            "deadline": task.get("deadline") or task.get("due_date") or task.get("due"),
            "status": normalize_task_status(task.get("status")),
            "priority": normalize_task_priority(task.get("priority")),
            "room_id": task.get("room_id") or task.get("conversation_id"),
            "document_id": task.get("document_id"),
            "created_at": task.get("created_at"),
        })

    return normalized

# 프론트 요청에서 target_document_id와 target_filename을 결정
def _resolve_target_document(request: ChatRequest) -> tuple[str | None, str | None]:
    target_document_id = request.target_document_id
    target_filename = request.target_filename

    if not target_document_id and target_filename:
        matched = get_document_by_filename_and_conversation(request.room_id, target_filename)
        if matched:
            target_document_id = matched.get("id")
            target_filename = matched.get("title")

    if not target_document_id and not target_filename and is_document_reference_message(request.content):
        latest = get_latest_document_by_conversation(request.room_id)
        if latest:
            target_document_id = latest.get("id")
            target_filename = latest.get("title")

    return target_document_id, target_filename

# AgentState를 프론트 응답 형식으로 변환
def build_chat_response(state: AgentState) -> ChatResponseSchema:
    retrieved_docs = state.get("retrieved_docs") or []

    graph_data = {
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
    }

    return ChatResponseSchema(
        room_id=state.get("room_id", ""),
        answer=state.get("final_answer") or "",
        summary=state.get("summary"),
        tasks=to_json_safe(normalize_tasks(state.get("tasks", []))),
        sources=to_json_safe(normalize_sources(state.get("sources", []))),
        notion_result=to_json_safe(state.get("notion_result")),
        graph_data=to_json_safe(graph_data),
        error=state.get("error"),
    )


# AgentState를 LangGraph에 전달해서 실행
def run_agent_graph(state: AgentState) -> AgentState:
    return agent_graph.invoke(state)


# AgentState 초기화
def create_initial_state(request: ChatRequest, messages: list | None = None) -> AgentState:
    """ChatRequest를 LangGraph에서 사용할 AgentState로 변환한다."""
    target_document_id, target_filename = _resolve_target_document(request)

    if target_document_id:
        rag_filter = {"document_id": target_document_id}
    elif target_filename:
        rag_filter = {"filename": target_filename}
    else:
        rag_filter = None

    return {
        "room_id": request.room_id,
        "user_message": request.content,
        "source": request.source,
        "created_at": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(),
        "messages": normalize_messages_for_state(messages),
        "document_json": None,
        "memory_context": None,
        "rag_context": None,
        "rag_search_result": None,
        "retrieved_docs": [],
        "low_confidence": False,
        "sources": [],
        "target_document_id": target_document_id,
        "target_filename": target_filename,
        "rag_filter": rag_filter,
        "question_type": "general_answer",
        "need_general_answer": True,
        "need_memory": False,
        "need_rag": False,
        "need_task_extract": False,
        "need_notion_save": False,
        "summary": None,
        "tasks": [],
        "final_answer": None,
        "save_target_content": None,
        "notion_result": None,
        "graph_data": None,
        "current_step": "chat_service",
        "error": None,
    }


# 채팅 처리
# 채팅 요청을 처리하고 최종 응답을 반환
async def handle_chat(request: ChatRequest) -> ChatResponseSchema:
    insert_message(conversation_id=request.room_id, role="user", content=request.content)

    messages = get_messages(request.room_id)
    state = create_initial_state(request, messages=messages)

    result_state = await asyncio.to_thread(run_agent_graph, state)

    answer = result_state.get("final_answer") or "응답을 생성하지 못했습니다."
    insert_message(conversation_id=request.room_id, role="assistant", content=answer)

    return build_chat_response(result_state)