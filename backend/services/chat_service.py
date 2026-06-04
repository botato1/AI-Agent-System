# 채팅 요청 처리 서비스
from datetime import datetime

from backend.schemas.chat_schema import ChatRequest
from backend.schemas.response_schema import ChatResponseSchema
from backend.schemas.agent_schema import AgentState
from backend.db.crud import insert_message
from backend.services.ollama_service import ollama_service

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

        # 6. Notion / Graph / 오류 결과
        "notion_result": None,
        "graph_data": None,
        "current_step": "chat_service",
        "error": None,
    }


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
    return ChatResponseSchema(
        room_id=state["room_id"],
        answer=answer,
        summary=state["summary"],
        tasks=state["tasks"],
        sources=[],
        notion_result=state["notion_result"],
        graph_data={
            "current_step": state["current_step"],
            "question_type": state["question_type"],
            "need_general_answer": state["need_general_answer"],
            "need_memory": state["need_memory"],
            "need_rag": state["need_rag"],
            "need_task_extract": state["need_task_extract"],
            "need_notion_save": state["need_notion_save"],
            "ollama": {
                "status": ollama_result.get("status"),
                "original_input": ollama_result.get("original_input"),
                "normalized_input": ollama_result.get("normalized_input"),
                "intent": ollama_result.get("intent"),
                "sources": sources,
            }
        },
        error=error,
    )
