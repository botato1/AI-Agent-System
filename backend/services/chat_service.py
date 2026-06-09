# 채팅 요청 처리 서비스
import asyncio
from datetime import datetime

from backend.schemas.chat_schema import ChatRequest
from backend.schemas.response_schema import ChatResponseSchema
from backend.schemas.agent_schema import AgentState
from backend.db.crud import insert_message
from backend.services.ollama_service import ollama_service
from backend.graphs.agent_graph import agent_graph

# ChatRequest를 LangGraph에서 사용할 AgentState로 변환하는 함수
def create_initial_state(request: ChatRequest) -> AgentState:

    return {
        # 1. 채팅 기본 정보
        "room_id": request.room_id,
        "user_message": request.content,
        "source": request.source,
        "created_at": datetime.now().isoformat(),
        "messages": [],

        # 2. 문서 / STT / 파일 처리 결과
        "document_json": None,

        # 3. 이전 대화 / RAG 검색 결과
        "memory_context": None,
        "rag_context": None,
        "sources": [],

        "target_document_id": request.target_document_id,
        "target_filename": request.target_filename,
        "rag_filter": (
            {"document_id": request.target_document_id}
            if request.target_document_id
            else {"filename": request.target_filename}
            if request.target_filename
            else None
        ),

        # 4. 질문 유형 판단 결과
        "question_type": "general",
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

# AgentState를 프론트 응답 형식으로 반환하는 함수
# 현재는 ollama_service 결과를 함께 사용하고 나중에 LangGraph 결과 state만 받아도 응답을 만들 수 있도록 분리
def build_chat_response(state: AgentState) -> ChatResponseSchema:
    raw_sources = state.get("sources", [])
    sources = normalize_sources(raw_sources)

    return ChatResponseSchema(
        room_id=state.get("room_id", ""),
        answer=state.get("final_answer") or "",
        summary=state.get("summary"),
        tasks=state.get("tasks", []),
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

    # 2. ChatRequest를 AgentState로 변환
    state = create_initial_state(request)

    # 3. LangGraph 실행
    # FastAPI async event loop 안에서 LangGraph sync invoke를 직접 실행하면
    # rag_node 내부 asyncio.run()과 충돌할 수 있으므로 별도 thread에서 실행
    result_state = await asyncio.to_thread(run_agent_graph, state)

    # 4. 최종 답변 추출
    answer = result_state.get("final_answer") or "응답을 생성하지 못했습니다."

    # 5. assistant 답변 DB 저장
    insert_message(
        conversation_id=request.room_id,
        role="assistant",
        content=answer
    )

    # 6. 최종 응답 반환
    return build_chat_response(result_state)

'''
# 채팅 요청을 처리하는 함수
async def handle_chat(request: ChatRequest) -> ChatResponseSchema:

    # 1. 사용자 메시지 DB 저장
    insert_message(
        conversation_id=request.room_id,
        role="user",
        content=request.content
    )

    # 2. ChatRequest를 AgentState로 변환
    state = create_initial_state(request)

    # 3. OllamaService 호출
    ollama_result = await ollama_service.process_query(
        user_input=request.content,
        conversation_id=request.room_id
    )

    # 4. OllamaService 결과 정리
    answer = ollama_result.get("answer", "응답을 생성하지 못했습니다.")
    intent = ollama_result.get("intent", "general")
    sources = ollama_result.get("sources", [])
    error = ollama_result.get("error")

    # 5. AgentState 업데이트
    state["question_type"] = intent
    state["final_answer"] = answer
    state["sources"] = sources
    state["error"] = error
    state["current_step"] = "ollama_service"

    # 6. intent에 따라 필요한 작업 표시
    if intent == "rag_search":
        state["need_rag"] = True
        state["need_general_answer"] = False

    elif intent == "task_extract":
        state["need_task_extract"] = True
        state["need_rag"] = True
        state["need_general_answer"] = False
    
    elif intent == "notion_save":
        state["need_notion_save"] = True
        state["need_general_answer"] = False

    else:
        state["need_general_answer"] = True

    # 7. assistant 답변 DB 저장
    insert_message(
        conversation_id=request.room_id,
        role="assistant",
        content=answer
    )

    # 8. 최종 응답 반환
    return build_chat_response(state, ollama_result)
'''

