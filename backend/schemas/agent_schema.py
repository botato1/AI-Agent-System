from typing import TypedDict, List, Optional


class AgentState(TypedDict):
    # 1. 채팅 기본 정보
    room_id: str
    user_message: str
    source: str
    created_at: str
    messages: List[dict]

    # 2. 문서 / STT / 파일 처리 결과
    document_json: Optional[dict]

    # 3. 이전 대화 / RAG 검색 결과
    memory_context: Optional[str]
    rag_context: Optional[str]
    sources: List[dict]

    target_document_id: Optional[str]
    target_filename: Optional[str]
    rag_filter: Optional[dict]

    # 4. 질문 유형 판단 결과
    question_type: str
    need_general_answer: bool
    need_memory: bool
    need_rag: bool
    need_task_extract: bool
    need_notion_save: bool

    # 5. LLM / 업무 추출 결과
    summary: Optional[str]
    tasks: List[dict]
    final_answer: Optional[str]

    # Notion 저장 시 실제로 저장할 내용
    save_target_content: Optional[str]

    # 6. Notion / Graph / 오류 결과
    notion_result: Optional[dict]
    graph_data: Optional[dict]
    current_step: Optional[str]
    error: Optional[str]