import sys
import re
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
    def _extract_filename(query: str) -> str:
        """
        사용자 질문에서 파일명을 추출하는 헬퍼 함수
        예: "무도_하지마_7장_보고서.pdf를 보고" -> "무도_하지마_7장_보고서.pdf"
            "회의록 파일 요약해줘" -> "회의록"
        """
        # 1. 확장자가 포함된 파일명 추출 패턴 (.pdf, .docx, .xlsx, .txt 등)
        file_with_ext_match = re.search(r'([a-zA-Z0-9_\-가-힣]+?\.(?:pdf|docx|xlsx|txt|pptx|csv))', query)
        if file_with_ext_match:
            return file_with_ext_match.group(1)
        
        # 2. 확장자가 없지만 '보고서', '파일', '문서' 등의 단어 앞에 있는 파일명 유추
        # 조사 '를', '을', '에서', '보고' 등이 붙는 패턴 고려
        file_noun_match = re.search(r'([a-zA-Z0-9_\-가-힣]+?)(?:\.pdf)?(?:를|을|에서|보고|\s+파일|\s+문서)', query)
        if file_noun_match:
            extracted = file_noun_match.group(1).strip()
            # 단순 키워드(pdf, 문서 등) 자체는 파일명에서 제외
            if extracted not in ["pdf", "문서", "보고서", "파일", "자료", "첨부", "업로드"]:
                return extracted
                
        return None

    @staticmethod
    async def process_query(user_input: str, conversation_id: str = None) -> dict:
        """
        전체 파이프라인
        1. 은어/약어 → 표준 용어 변환
        2. 질문 의도 파악 및 RAG 필요 여부 결정
        3. 특정 파일 지정 여부 확인 후 메타데이터 필터 구성
        4. 의도 및 필터에 따라 RAG 검색 수행
        5. 최종 답변 반환
        """
        print(f"[OllamaService] 입력: '{user_input}'")

        try:
            # 1. 은어/약어 변환
            normalized = normalize_query(user_input)
            print(f"[OllamaService] 변환: '{normalized}'")

            # 2. 의도 파악
            intent_result = classify_intent(normalized)
            intent = intent_result.get("intent", "general")
            print(f"[OllamaService] 의도: {intent}")

            # RAG가 필수적인 인텐트 목록 정의
            rag_intents = {
                "rag_search",
                "document_summary",
                "document_question",
                "document_search",
                "past_record_search",
                "error_troubleshooting"
            }
            
            # 태스크/액션아이템 추출 인텐트 목록 정의
            task_intents = {"task_extract", "task_extraction"}

            # term_explanation 조건 검증을 위한 키워드 리스트
            rag_keywords = ["pdf", "문서", "보고서", "파일", "자료", "첨부", "업로드", "에서 찾아", "에서 확인", "에서 요약", "보고"]
            
            # RAG 필요 여부 기본 판단
            need_rag = False
            if intent in rag_intents or intent in task_intents:
                need_rag = True
            elif intent == "term_explanation":
                # 질문에 RAG 관련 키워드가 하나라도 포함되어 있는지 확인
                if any(keyword in normalized for keyword in rag_keywords):
                    need_rag = True

            # 3. 파일명 추출 및 필터 빌딩
            search_filter = {}
            extracted_filename = OllamaService._extract_filename(normalized)
            
            if extracted_filename:
                print(f"[OllamaService] 추출된 파일명: '{extracted_filename}'")
                # 우선순위 필터 적용을 위해 검색 시 매칭할 수 있도록 구성 (ChromaDB의 where 절 형식에 맞춤)
                # 시스템 환경에 따라 단일 조건 혹은 $or 조건을 사용합니다. 
                # 여기서는 질문에 나온 텍스트를 filename이나 title에서 매칭할 수 있도록 구성합니다.
                search_filter = {"filename": extracted_filename}
            
            # 회의록 추출 인텐트일 경우 기존의 'meeting' 타입 필터 결합
            if intent in task_intents:
                search_filter["type"] = "meeting"

            # 4. RAG 검색 수행
            rag_context = ""
            sources = []

            if need_rag:
                # 인텐트별 검색 top_k 개수 조정
                top_k = 3 if intent in task_intents else 5
                
                # 가공된 search_filter를 포함하여 RAG 검색 요청
                rag_result = await rag_service.retrieve_relevant_knowledge(
                    query=normalized,
                    top_k=top_k,
                    filter=search_filter if search_filter else None
                )

                if rag_result and rag_result.get("count", 0) > 0:
                    # 검색된 문서 컨텍스트로 합치기
                    rag_context = "\n\n".join([
                        doc.get("content", "") for doc in rag_result["data"]
                    ])
                    
                    # 요청하신 dict 구조로 sources 목록 생성
                    sources = [
                        {
                            "id": doc.get("id") or doc.get("document_id"),
                            "document_id": doc.get("document_id") or doc.get("id"),
                            "filename": doc.get("filename"),
                            "title": doc.get("title"),
                            "source": doc.get("source") or doc.get("filename") or doc.get("title"),
                            "score": doc.get("score"),
                        }
                        for doc in rag_result["data"]
                    ]

            # 5. 최종 답변 생성
            answer = generate_answer(user_input, context=rag_context)

            return {
                "status": "success",
                "original_input": user_input,
                "normalized_input": normalized,
                "question_type": intent, 
                "intent": intent,
                "need_rag": need_rag,  
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
                "question_type": "general",
                "intent": "general",
                "need_rag": False,
                "answer": "처리 중 오류가 발생했습니다.",
                "sources": [],
                "error": str(e)
            }

ollama_service = OllamaService()