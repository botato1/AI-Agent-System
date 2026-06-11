import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from backend.modules.llm.ollama_client import (
    normalize_query,
    classify_intent,
    generate_answer_for_graph as client_generate_answer_for_graph,
    extract_tasks_from_content as client_extract_tasks_from_content,
    generate_summary_for_notion as client_generate_summary_for_notion,
)
from backend.services.rag_service import rag_service


class OllamaService:
    """
    LangGraph node에서 재사용할 LLM/RAG 보조 함수 모음.

    LLM 프롬프트 생성과 Ollama 호출은 ollama_client.py에서 담당하고,
    이 서비스는 LangGraph용 분류 보정, RAG filter 생성, sources 정리,
    client 함수 호출 역할만 담당한다.
    """

    # 한글 파일명 비교를 위해 문자열을 NFC 기준으로 정규화하는 함수
    @staticmethod
    def normalize_text(value: str | None) -> str:
        if not value:
            return ""

        return unicodedata.normalize("NFC", value).strip()

    # 사용자 입력을 정규화하는 함수
    @staticmethod
    def normalize_user_input(user_input: str) -> str:
        normalized = normalize_query(user_input)
        return OllamaService.normalize_text(normalized)

    # 사용자 질문에서 파일명을 추출하는 함수
    @staticmethod
    def extract_filename(query: str) -> str | None:
        query = OllamaService.normalize_text(query)

        pattern = r"([가-힣a-zA-Z0-9_\-\s]+?\.(?:pdf|docx|doc|md|xlsx|txt|pptx|csv))"
        match = re.search(pattern, query, re.IGNORECASE)

        if match:
            return OllamaService.normalize_text(match.group(1))

        return None

    # 이전 대화가 필요한 요청인지 키워드로 보정하는 함수
    @staticmethod
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
            "전에 말한",
        ]

        return any(keyword in message for keyword in message and memory_keywords)

    # Notion 저장 요청인지 키워드로 보정하는 함수
    @staticmethod
    def is_notion_save_request(message: str) -> bool:
        message_lower = message.lower()

        notion_keywords = ["노션", "notion"]
        save_keywords = ["저장", "기록", "보관", "정리해줘", "올려줘"]

        return (
            any(keyword in message_lower for keyword in notion_keywords)
            and any(keyword in message for keyword in save_keywords)
        )

    # 문서 관련 요청인지 키워드로 보정하는 함수
    @staticmethod
    def is_document_request(message: str) -> bool:
        document_keywords = [
            "pdf",
            "PDF",
            "문서",
            "보고서",
            "파일",
            "자료",
            "첨부",
            "업로드",
            "회의록",
            "에서 찾아",
            "에서 확인",
            "에서 요약",
            "기반으로",
            "참고해서",
        ]

        return any(keyword in message for keyword in document_keywords)

    # 문서 요약 요청인지 키워드로 보정하는 함수
    @staticmethod
    def is_summary_request(message: str) -> bool:
        summary_keywords = [
            "요약",
            "정리",
            "핵심",
            "내용 알려",
            "내용 설명",
        ]

        return any(keyword in message for keyword in summary_keywords)

    # 할 일 추출 요청인지 키워드로 보정하는 함수
    @staticmethod
    def is_task_request(message: str) -> bool:
        task_keywords = [
            "할 일",
            "해야 할 일",
            "업무",
            "태스크",
            "task",
            "담당자",
            "마감일",
            "액션아이템",
            "액션 아이템",
        ]

        return any(keyword in message for keyword in task_keywords)

    # LLM intent 결과를 LangGraph AgentState flag로 변환하는 함수
    @staticmethod
    def map_intent_to_agent_flags(intent: str) -> dict[str, Any]:
        # 이전 intent 이름과 호환 처리
        if intent == "task_extraction":
            intent = "task_extract"

        if intent == "past_record_search":
            intent = "memory_search"

        result = {
            "question_type": "general",
            "need_general_answer": True,
            "need_memory": False,
            "need_rag": False,
            "need_task_extract": False,
            "need_notion_save": False,
        }

        if intent == "document_summary":
            result["question_type"] = "document_summary"
            result["need_rag"] = True

        elif intent == "document_question":
            result["question_type"] = "document_question"
            result["need_rag"] = True

        elif intent == "task_extract":
            result["question_type"] = "task_extract"
            result["need_rag"] = True
            result["need_task_extract"] = True

        elif intent == "notion_save":
            result["question_type"] = "notion_save"
            result["need_notion_save"] = True

        elif intent == "memory_search":
            result["question_type"] = "memory_search"
            result["need_memory"] = True

        elif intent == "error_troubleshooting":
            result["question_type"] = "error_troubleshooting"
            result["need_rag"] = True

        elif intent == "term_explanation":
            result["question_type"] = "term_explanation"

        else:
            result["question_type"] = "general"

        result["need_general_answer"] = not (
            result["need_memory"]
            or result["need_rag"]
            or result["need_task_extract"]
            or result["need_notion_save"]
        )

        return result

    # LangGraph classifier_node에서 사용할 의도 분류 함수
    @staticmethod
    def classify_for_graph(user_input: str) -> dict[str, Any]:
        normalized = OllamaService.normalize_user_input(user_input)

        try:
            intent_result = classify_intent(normalized)
            intent = intent_result.get("intent", "general")
        except Exception as e:
            print(f"[OllamaService classify_for_graph 에러]: {str(e)}")
            intent = "general"

        mapped = OllamaService.map_intent_to_agent_flags(intent)

        target_filename = OllamaService.extract_filename(normalized)

        memory_request = OllamaService.is_memory_request(normalized)
        notion_save_request = OllamaService.is_notion_save_request(normalized)
        document_request = OllamaService.is_document_request(normalized)
        summary_request = OllamaService.is_summary_request(normalized)
        task_request = OllamaService.is_task_request(normalized)

        # flag를 먼저 모두 계산
        need_memory = mapped.get("need_memory", False) or memory_request
        need_notion_save = mapped.get("need_notion_save", False) or notion_save_request
        need_task_extract = mapped.get("need_task_extract", False) or task_request
        need_rag = mapped.get("need_rag", False)

        if target_filename or document_request:
            need_rag = True

        if need_task_extract:
            need_rag = True

        # 방금/이전 답변을 Notion에 저장하는 경우는 RAG를 타지 않음
        if need_notion_save and need_memory and not need_task_extract:
            need_rag = False

        # question_type은 마지막에 우선순위 기준으로 한 번만 결정
        if need_task_extract:
            question_type = "task_extract"
        elif need_notion_save and need_memory:
            question_type = "notion_save"
        elif need_notion_save and not need_rag:
            question_type = "notion_save"
        elif need_memory:
            question_type = "memory_search"
        elif need_rag and summary_request:
            question_type = "document_summary"
        elif need_rag:
            question_type = mapped.get("question_type")
            if question_type not in {
                "document_summary",
                "document_question",
                "error_troubleshooting",
            }:
                question_type = "document_question"
        elif intent == "term_explanation":
            question_type = "term_explanation"
        else:
            question_type = "general"

        need_general_answer = not (
            need_memory
            or need_rag
            or need_task_extract
            or need_notion_save
        )

        return {
            "question_type": question_type,
            "intent": intent,
            "normalized_input": normalized,
            "need_general_answer": need_general_answer,
            "need_memory": need_memory,
            "need_rag": need_rag,
            "need_task_extract": need_task_extract,
            "need_notion_save": need_notion_save,
            "target_filename": target_filename,
        }

    # RAG 검색 filter를 생성하는 함수
    @staticmethod
    def build_rag_filter(
        target_document_id: str | None = None,
        target_filename: str | None = None,
        existing_filter: dict | None = None,
    ) -> dict | None:
        if existing_filter:
            return existing_filter

        if target_document_id:
            return {"document_id": target_document_id}

        if target_filename:
            return {"filename": OllamaService.normalize_text(target_filename)}

        return None

    # RAG 검색 결과에서 중복 문서 chunk를 제거하는 함수
    @staticmethod
    def deduplicate_docs(docs: list[dict]) -> list[dict]:
        seen = set()
        unique_docs = []

        for doc in docs:
            title = OllamaService.normalize_text(doc.get("title"))
            content = (doc.get("content") or "").strip()

            dedupe_key = (
                title,
                content,
            )

            if dedupe_key in seen:
                continue

            seen.add(dedupe_key)
            unique_docs.append(doc)

        return unique_docs

    # RAG 검색 결과를 응답용 sources 구조로 변환하는 함수
    @staticmethod
    def format_sources(docs: list[dict]) -> list[dict]:
        sources = []
        seen = set()

        for doc in docs:
            title = doc.get("title")
            source = doc.get("source") or doc.get("filename") or title

            dedupe_key = (
                OllamaService.normalize_text(title),
                OllamaService.normalize_text(source),
            )

            if dedupe_key in seen:
                continue

            seen.add(dedupe_key)

            sources.append(
                {
                    "id": doc.get("id") or doc.get("document_id") or doc.get("chroma_id"),
                    "title": title,
                    "source": source,
                    "source_url": doc.get("source_url"),
                    "data_type": doc.get("data_type"),
                    "score": doc.get("score"),
                    "importance": doc.get("importance") or doc.get("importance_score"),
                    "created_at": doc.get("created_at"),
                    "notion_url": doc.get("notion_url"),
                    "tags": doc.get("tags"),
                }
            )

        return sources

    # 파일명이 title에 포함되어 있는지 NFC 정규화 후 비교하는 함수
    @staticmethod
    def filename_in_title(target_filename: str | None, title: str | None) -> bool:
        normalized_filename = OllamaService.normalize_text(target_filename)
        normalized_title = OllamaService.normalize_text(title)

        if not normalized_filename or not normalized_title:
            return False

        return normalized_filename in normalized_title

    # answer_node에서 사용할 답변 생성 함수 호출
    @staticmethod
    def generate_answer_for_graph(
        user_message: str,
        question_type: str = "general",
        rag_context: str | None = None,
        memory_context: str | None = None,
        tasks: list | None = None,
    ) -> str:
        return client_generate_answer_for_graph(
            user_message=user_message,
            question_type=question_type,
            rag_context=rag_context or "",
            memory_context=memory_context or "",
            tasks=tasks or [],
        )

    # task_node에서 사용할 할 일 추출 함수 호출
    @staticmethod
    def extract_tasks_from_content(content: str) -> list[dict]:
        return client_extract_tasks_from_content(content)

    # notion_node에서 사용할 Notion 저장용 요약 생성 함수 호출
    @staticmethod
    def generate_summary_for_notion(content: str) -> str | None:
        return client_generate_summary_for_notion(content)

    # 단일 파이프라인 테스트용 함수
    @staticmethod
    def process_query(user_input: str, conversation_id: str = None) -> dict:
        try:
            classified = OllamaService.classify_for_graph(user_input)

            rag_context = ""
            sources = []

            if classified.get("need_rag"):
                rag_filter = OllamaService.build_rag_filter(
                    target_filename=classified.get("target_filename")
                )

                rag_result = rag_service.retrieve_relevant_knowledge_sync(
                    query=classified.get("normalized_input") or user_input,
                    top_k=5,
                    filter=rag_filter,
                    question_type=classified.get("question_type", "general"),
                )

                if rag_result and rag_result.get("count", 0) > 0:
                    docs = OllamaService.deduplicate_docs(rag_result.get("data", []))

                    rag_context = "\n\n".join(
                        [
                            doc.get("content", "")
                            for doc in docs
                            if doc.get("content")
                        ]
                    )

                    sources = OllamaService.format_sources(docs)

            answer = OllamaService.generate_answer_for_graph(
                user_message=user_input,
                question_type=classified.get("question_type", "general"),
                rag_context=rag_context,
            )

            return {
                "status": "success",
                "original_input": user_input,
                "normalized_input": classified.get("normalized_input"),
                "question_type": classified.get("question_type"),
                "intent": classified.get("intent"),
                "need_rag": classified.get("need_rag"),
                "answer": answer,
                "sources": sources,
                "error": None,
            }

        except Exception as e:
            print(f"[OllamaService 에러]: {str(e)}")

            return {
                "status": "error",
                "original_input": user_input,
                "normalized_input": user_input,
                "question_type": "general",
                "intent": "general",
                "need_rag": False,
                "answer": "처리 중 오류가 발생했습니다.",
                "sources": [],
                "error": str(e),
            }


ollama_service = OllamaService()