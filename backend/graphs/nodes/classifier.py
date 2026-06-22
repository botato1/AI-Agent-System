from backend.schemas.agent_schema import AgentState
from backend.services.ollama_service import ollama_service


# 사용자 메시지를 분석해서 question_type과 필요 노드를 판단하는 노드
def classifier_node(state: AgentState) -> AgentState:
    user_message = state.get("user_message", "")
    user_message_lower = user_message.lower()

    try:
        classified = ollama_service.classify_for_graph(user_message)

        # 1. LLM이 분류한 question_type 가져오기
        question_type = classified.get("question_type", "general_answer")

        # 2. 5개 question_type 외 값이 들어오면 general_answer로 처리
        valid_question_types = {
            "task_from_rag",
            "task_from_memory",
            "notion_save",
            "knowledge_search",
            "general_answer",
        }

        if question_type not in valid_question_types:
            question_type = "general_answer"

        # 3. 프론트에서 넘어온 문서 정보 확인
        target_document_id = state.get("target_document_id")
        target_filename = ollama_service.normalize_text(
            state.get("target_filename") or classified.get("target_filename")
        )

        rag_filter = state.get("rag_filter")

        # 4. 프론트에서 선택 문서가 넘어온 경우 document_id 우선
        if target_document_id:
            rag_filter = {"document_id": target_document_id}

        # 5. 파일명이 명시된 경우 filename filter 준비
        elif target_filename:
            rag_filter = {"filename": target_filename}

        # 6. 문서 기반 요청인지 판단
        document_target_keywords = [
            "이 문서",
            "해당 문서",
            "선택한 문서",
            "업로드한 문서",
            "첨부한 문서",
            "문서에서",
            "문서를 기반",
            "문서 기반",
            "이 파일",
            "해당 파일",
            "선택한 파일",
            "업로드한 파일",
            "첨부한 파일",
            "파일에서",
            "파일을 기반",
            "이 pdf",
            "해당 pdf",
            "pdf에서",
            "회의록에서",
            "회의록 기반",
        ]

        # Notion 저장 요청 중 문서/자료/회의록을 저장하라는 표현 확인용
        document_save_keywords = [
            "문서",
            "파일",
            "pdf",
            "자료",
            "회의록",
            "보고서",
        ]

        task_keywords = [
            "할 일",
            "할일",
            "업무",
            "작업",
            "담당",
            "마감",
            "정리",
            "추출",
            "뽑아",
        ]

        knowledge_keywords = [
            "요약",
            "설명",
            "알려줘",
            "내용",
            "정리해줘",
            "무슨 내용",
            "뭐야",
        ]

        memory_target_keywords = [
            "지금까지",
            "대화에서",
            "대화 내용",
            "아까",
            "방금",
            "방금 추출",
            "방금 정리",
            "위에서",
            "이전 대화",
            "이전 답변",
            "채팅 내용",
            "말한 내용",
            "추출한 할 일",
            "추출한 할일",
            "할 일 목록",
            "할일 목록",
        ]

        notion_save_keywords = [
            "노션에 저장",
            "노션 저장",
            "notion에 저장",
            "notion 저장",
            "노션에 기록",
            "노션 기록",
            "노션에 적어",
            "노션에 올려",
            "notion에 기록",
            "notion에 적어",
            "notion에 올려",
        ]

        has_document_target = bool(target_document_id or target_filename)

        mentions_document_target = any(
            keyword in user_message_lower
            for keyword in document_target_keywords
        )

        mentions_document_save_target = any(
            keyword in user_message_lower
            for keyword in document_save_keywords
        )

        mentions_task = any(
            keyword in user_message
            for keyword in task_keywords
        )

        mentions_knowledge = any(
            keyword in user_message
            for keyword in knowledge_keywords
        )

        mentions_memory_target = any(
            keyword in user_message
            for keyword in memory_target_keywords
        )

        # "노션"과 "저장/기록/적어/올려"가 같이 있으면 저장 요청으로 판단
        mentions_notion_save = (
            any(keyword in user_message_lower for keyword in notion_save_keywords)
            or (
                ("노션" in user_message_lower or "notion" in user_message_lower)
                and any(keyword in user_message for keyword in ["저장", "기록", "적어", "올려"])
            )
        )

        # 7. 문서 기반 할 일 추출 요청 보정
        # 예: "이 문서에서 해야 할 일 정리해줘"
        if has_document_target and mentions_document_target and mentions_task:
            question_type = "task_from_rag"

        # 8. 문서 기반 요약/질문 요청 보정
        # 예: "이 문서 요약해줘", "이 파일 내용 알려줘"
        if (
            has_document_target
            and mentions_document_target
            and mentions_knowledge
            and question_type == "general_answer"
        ):
            question_type = "knowledge_search"

        # 9. 대화 기반 할 일 추출 요청 보정
        # 일반 업무 문장을 task_from_memory로 잘못 분류하는 경우 방지
        if question_type == "task_from_memory" and not mentions_memory_target:
            question_type = "general_answer"

        # 10. Notion 저장 요청은 최우선 보정
        # 예: "방금 추출한 할 일 목록을 노션에 저장해줘"
        # 예: "이 문서를 노션에 저장해줘"
        if mentions_notion_save:
            question_type = "notion_save"

        # 11. notion_save가 문서 기반인지, 대화/이전 결과 기반인지 구분
        notion_requires_rag = (
            question_type == "notion_save"
            and (
                has_document_target
                or mentions_document_target
                or mentions_document_save_target
            )
            and not mentions_memory_target
        )

        notion_requires_memory = (
            question_type == "notion_save"
            and not notion_requires_rag
        )

        # 12. question_type 기준으로 need_* 값 정리
        need_memory = (
            question_type == "task_from_memory"
            or notion_requires_memory
        )

        need_rag = (
            question_type in {
                "task_from_rag",
                "knowledge_search",
            }
            or notion_requires_rag
        )

        need_task_extract = question_type in {
            "task_from_rag",
            "task_from_memory",
        }

        need_notion_save = question_type == "notion_save"

        need_general_answer = question_type == "general_answer"

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