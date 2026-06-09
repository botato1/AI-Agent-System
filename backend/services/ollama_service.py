import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from backend.modules.llm.ollama_client import (
    normalize_query,
    classify_intent,
    generate_answer
)
from backend.modules.rag.chroma_client import search_hybrid
from backend.services.rag_service import rag_service

class OllamaService:

    @staticmethod
    async def process_query(user_input: str, conversation_id: str = None) -> dict:
        """
        전체 파이프라인
        1. 은어/약어 → 표준 용어 변환
        2. 질문 의도 파악
        3. 의도에 따라 RAG 검색 or 일반 답변
        4. 최종 답변 반환
        """
        print(f"[OllamaService] 입력: '{user_input}'")

        try:
            # 1. 은어/약어 변환
            normalized = normalize_query(user_input)
            print(f"[OllamaService] 변환: '{normalized}'")

            # 2. 의도 파악
            intent_result = classify_intent(normalized)
            intent = intent_result["intent"]
            print(f"[OllamaService] 의도: {intent}")

            # 3. 의도별 처리
            rag_context = ""
            sources = []

            if intent == "rag_search":
                # RAG 검색
                rag_result = rag_service.retrieve_relevant_knowledge(
                    query=normalized,
                    top_k=5
                )
                if rag_result["count"] > 0:
                    # 검색된 문서 컨텍스트로 합치기
                    rag_context = "\n\n".join([
                        doc["content"] for doc in rag_result["data"]
                    ])
                    sources = [
                        doc["title"] for doc in rag_result["data"]
                    ]

            elif intent == "task_extract":
                # 액션아이템 추출용 RAG 검색 (회의록만)
                rag_result = rag_service.retrieve_relevant_knowledge(
                    query=normalized,
                    top_k=3,
                    filter={"type": "meeting"}
                )
                if rag_result["count"] > 0:
                    rag_context = "\n\n".join([
                        doc["content"] for doc in rag_result["data"]
                    ])
                    sources = [doc["title"] for doc in rag_result["data"]]

            # 4. 최종 답변 생성
            answer = generate_answer(user_input, context=rag_context)

            return {
                "status": "success",
                "original_input": user_input,
                "normalized_input": normalized,
                "intent": intent,
                "answer": answer,
                "sources": sources,
                "error": None
            }

        except Exception as e:
            print(f"[OllamaService 에러]: {str(e)}")
            return {
                "status": "error",
                "original_input": user_input,
                "normalized_input": user_input,
                "intent": "general",
                "answer": "처리 중 오류가 발생했습니다.",
                "sources": [],
                "error": str(e)
            }

ollama_service = OllamaService()