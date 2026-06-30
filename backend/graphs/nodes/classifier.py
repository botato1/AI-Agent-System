from backend.schemas.agent_schema import AgentState
from backend.services.ollama_service import ollama_service


# 키워드 상수
VALID_QUESTION_TYPES = {
    "task_from_rag",
    "task_from_memory",
    "notion_save",
    "knowledge_search",
    "general_answer",
    "summary_from_rag",
}

DOCUMENT_TARGET_KEYWORDS = [
    "이 문서", "해당 문서", "선택한 문서", "업로드한 문서", "첨부한 문서",
    "문서에서", "문서를 기반", "문서 기반",
    "이 파일", "해당 파일", "선택한 파일", "업로드한 파일", "첨부한 파일",
    "파일에서", "파일을 기반",
    "이 pdf", "해당 pdf", "pdf에서",
    "회의록에서", "회의록 기반",
]

DOCUMENT_SAVE_KEYWORDS = [
    "문서", "파일", "pdf", "자료", "회의록", "보고서",
]

TASK_KEYWORDS = [
    "할 일", "할일", "업무", "작업", "담당", "마감", "정리", "추출", "뽑아",
]

KNOWLEDGE_KEYWORDS = [
    "설명", "알려줘", "내용", "정리해줘", "무슨 내용", "뭐야",
]

SUMMARY_KEYWORDS = [
    "요약", "요약해줘", "요약해", "요약본", "summary",
]

# 다중 문서 비교 요청 키워드. summary_from_rag로 보정해서
# 여러 문서의 내용을 종합해서 답변하도록 유도한다.
COMPARE_KEYWORDS = [
    "비교", "비교해줘", "비교해", "차이", "차이점", "다른점", "다른 점",
    "공통점", "공통", "어떻게 달라", "뭐가 달라",
]

MEMORY_TARGET_KEYWORDS = [
    "지금까지", "대화에서", "대화 내용", "아까", "방금",
    "방금 추출", "방금 정리", "위에서", "이전 대화", "이전 답변",
    "채팅 내용", "말한 내용",
    "추출한 할 일", "추출한 할일", "할 일 목록", "할일 목록",
]

NOTION_SAVE_KEYWORDS = [
    "노션에 저장", "노션 저장", "notion에 저장", "notion 저장",
    "노션에 기록", "노션 기록", "노션에 적어", "노션에 올려",
    "notion에 기록", "notion에 적어", "notion에 올려",
]

NOTION_ACTION_KEYWORDS = ["저장", "기록", "적어", "올려"]


# helper 함수
def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _detect_notion_save(message: str, message_lower: str) -> bool:
    if _contains_any(message_lower, NOTION_SAVE_KEYWORDS):
        return True

    is_notion = "노션" in message_lower or "notion" in message_lower
    has_action = _contains_any(message, NOTION_ACTION_KEYWORDS)

    return is_notion and has_action


def _resolve_question_type(question_type: str, has_document_target: bool, mentions_document_target: bool, mentions_task: bool,
    mentions_knowledge: bool, mentions_summary: bool, mentions_compare: bool, mentions_memory_target: bool, mentions_notion_save: bool) -> str:
    if mentions_notion_save:
        return "notion_save"

    # 문서 타겟 + 요약/비교 키워드 → summary_from_rag로 보정
    # (knowledge_search로 잘못 분류되는 것을 방지)
    if has_document_target and mentions_document_target and (mentions_summary or mentions_compare):
        return "summary_from_rag"

    if (
        has_document_target
        and mentions_document_target
        and mentions_knowledge
        and question_type == "general_answer"
    ):
        return "knowledge_search"

    if has_document_target and mentions_document_target and mentions_task:
        return "task_from_rag"

    # 문서 타겟이 있고 문서 관련 키워드가 있으면 summary_from_rag로 보정
    if (
        has_document_target
        and mentions_document_target
        and question_type == "general_answer"
    ):
        return "summary_from_rag"

    # task_from_rag인데 문서 타겟이 없으면 general_answer로 보정
    if question_type == "task_from_rag" and not has_document_target and not mentions_document_target:
        return "general_answer"

    if question_type == "task_from_memory" and not mentions_memory_target:
        return "general_answer"

    return question_type


def _build_need_flags(question_type: str, has_document_target: bool, mentions_document_target: bool,
    mentions_document_save_target: bool, mentions_memory_target: bool) -> dict:
    notion_requires_rag = (
        question_type == "notion_save"
        and (has_document_target or mentions_document_target or mentions_document_save_target)
        and not mentions_memory_target
    )

    notion_requires_memory = (
        question_type == "notion_save"
        and not notion_requires_rag
    )

    return {
        "need_memory": question_type == "task_from_memory" or notion_requires_memory,
        "need_rag": question_type in {"task_from_rag", "knowledge_search", "summary_from_rag"} or notion_requires_rag,
        "need_task_extract": question_type in {"task_from_rag", "task_from_memory"},
        "need_notion_save": question_type == "notion_save",
        "need_general_answer": question_type == "general_answer",
    }


# classifier_node
def classifier_node(state: AgentState) -> AgentState:
    user_message = state.get("user_message", "")
    user_message_lower = user_message.lower()

    try:
        classified = ollama_service.classify_for_graph(user_message)

        question_type = classified.get("question_type", "general_answer")

        if question_type not in VALID_QUESTION_TYPES:
            question_type = "general_answer"

        target_document_id = state.get("target_document_id")
        target_filename = ollama_service.normalize_text(
            state.get("target_filename") or classified.get("target_filename")
        )

        rag_filter = state.get("rag_filter")

        if target_document_id:
            rag_filter = {"document_id": target_document_id}
        elif target_filename:
            rag_filter = {"filename": target_filename}

        # rag_filter가 있으면 문서 타겟이 있다고 판단
        has_document_target = bool(target_document_id or target_filename or rag_filter)
        mentions_document_target = _contains_any(user_message_lower, DOCUMENT_TARGET_KEYWORDS)
        mentions_document_save_target = _contains_any(user_message_lower, DOCUMENT_SAVE_KEYWORDS)
        mentions_task = _contains_any(user_message, TASK_KEYWORDS)
        mentions_knowledge = _contains_any(user_message, KNOWLEDGE_KEYWORDS)
        mentions_summary = _contains_any(user_message_lower, SUMMARY_KEYWORDS)
        mentions_compare = _contains_any(user_message_lower, COMPARE_KEYWORDS)
        mentions_memory_target = _contains_any(user_message, MEMORY_TARGET_KEYWORDS)
        mentions_notion_save = _detect_notion_save(user_message, user_message_lower)

        question_type = _resolve_question_type(
            question_type=question_type,
            has_document_target=has_document_target,
            mentions_document_target=mentions_document_target,
            mentions_task=mentions_task,
            mentions_knowledge=mentions_knowledge,
            mentions_summary=mentions_summary,
            mentions_compare=mentions_compare,
            mentions_memory_target=mentions_memory_target,
            mentions_notion_save=mentions_notion_save,
        )

        need_flags = _build_need_flags(
            question_type=question_type,
            has_document_target=has_document_target,
            mentions_document_target=mentions_document_target,
            mentions_document_save_target=mentions_document_save_target,
            mentions_memory_target=mentions_memory_target,
        )

        return {
            **state,
            "question_type": question_type,
            **need_flags,
            "target_document_id": target_document_id,
            "target_filename": target_filename,
            "rag_filter": rag_filter,
            "current_step": "classifier_node",
            "error": None,
        }

    except Exception as e:
        return {
            **state,
            "question_type": "general_answer",
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