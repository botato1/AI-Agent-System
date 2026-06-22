# backend/services/rag_service.py
import sys
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from backend.modules.rag.chroma_client import (
    search_hybrid,
    rerank_results,
    MEETING_COLLECTION,
    DOCUMENT_COLLECTION,
    KNOWLEDGE_COLLECTION,
)

# ── 상수 ─────────────────────────────────────────────────────
CANDIDATE_K  = 60      # 하이브리드 검색에서 가져올 후보 수
SCALE_FACTOR = 0.0005  # tech_score 보정 가중치 (실측 후 조정)

# [추가 - 2026.06.18]
# 적재(크롤링) 단계의 "탈락시키지 않는다"는 원칙과는 별개로,
# 검색/답변 단계에서는 질문별로 실제 관련도가 다르므로 신뢰도 기준이 필요함.
# 8개 질문 실측 기준: 명확히 관련있는 케이스는 0.7~0.99, 무관한 케이스는
# 0.3 미만으로 나타남. 0.3을 임시 경계값으로 설정 (추가 테스트로 조정 필요).
LOW_CONFIDENCE_THRESHOLD = 0.3

MEETING_SIGNALS = [
    "회의", "저번에", "말했던", "논의", "액션아이템",
    "참석자", "지난", "미팅", "회의록",
]
DOCUMENT_SIGNALS = [
    "문서", "파일", "보냈던", "올린", "자료",
    "보고서", "pdf", "첨부",
]
KNOWLEDGE_SIGNALS = [
    "에러", "오류", "방법", "설치", "설정", "코드",
    "쿠버", "도커", "kubernetes", "docker", "pod",
    "배포", "파이프라인",
]


def get_utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _has_specific_document_filter(filter: dict | None) -> bool:
    if not filter:
        return False
    return bool(filter.get("document_id") or filter.get("filename"))


def _select_collections(
    question_type: str,
    query: str = "",
    filter: dict | None = None,
) -> list[str]:
    all_collections = [MEETING_COLLECTION, DOCUMENT_COLLECTION, KNOWLEDGE_COLLECTION]

    if _has_specific_document_filter(filter):
        return all_collections

    has_meeting   = any(s in query for s in MEETING_SIGNALS)
    has_document  = any(s in query for s in DOCUMENT_SIGNALS)
    has_knowledge = any(s in query for s in KNOWLEDGE_SIGNALS)

    targets = set()
    if has_meeting:   targets.add(MEETING_COLLECTION)
    if has_document:  targets.add(DOCUMENT_COLLECTION)
    if has_knowledge: targets.add(KNOWLEDGE_COLLECTION)

    if question_type == "task_from_rag":
        targets.add(MEETING_COLLECTION)

    return list(targets) if targets else all_collections


class RAGService:

    @staticmethod
    def retrieve_relevant_knowledge(
        query: str,
        original_query: str = None,
        top_k: int = 5,
        relative_threshold: float = 0.5,  # 더 이상 필터링에 사용 안 함 (호환성 위해 파라미터만 유지)
        filter: dict = None,
        question_type: str = "general_answer",
    ):
        """
        흐름:
        1. _select_collections()로 검색할 컬렉션(들) 결정
        2. 각 컬렉션에서 하이브리드 검색 (후보 CANDIDATE_K개씩)
        3. 전체 후보를 reranker로 재평가
        4. final_score = reranker_score + tech_score*SCALE_FACTOR (knowledge만 보정)
        5. final_score 기준 정렬
        6. 상위 top_k개만 잘라서 반환 (적재 단계와 달리, 결과 자체는 탈락시키지
           않고 그대로 반환함. 다만 최고 점수가 LOW_CONFIDENCE_THRESHOLD 미만이면
           low_confidence=True로 표시해서, 답변 생성 단계(ollama_client)가
           "관련 문서를 찾지 못했다"는 안내와 함께 참고용으로만 보여주도록 함)
        """
        print(f"[RAG Service] 쿼리: '{query}' / 타입: '{question_type}'")
        print(f"[RAG Service] filter: {filter}")

        try:
            collections = _select_collections(
                question_type=question_type,
                query=query,
                filter=filter,
            )
            print(f"[RAG Service] 검색 컬렉션: {collections}")

            all_results = []
            seen_ids = set()

            for col in collections:
                results = search_hybrid(
                    query_text=query,
                    top_k=CANDIDATE_K,
                    filter=filter,
                    collection_name=col,
                )
                for r in results:
                    if r["id"] not in seen_ids:
                        seen_ids.add(r["id"])
                        all_results.append(r)

            if not all_results:
                return {
                    "status": "success",
                    "query": query,
                    "count": 0,
                    "data": [],
                    "low_confidence": True,
                    "error": None,
                }

            all_results = rerank_results(query, all_results)

            for res in all_results:
                reranker_score = res.get("reranker_score", 0.0)
                collection     = res.get("collection", "")

                if collection == KNOWLEDGE_COLLECTION:
                    tech_score = res.get("metadata", {}).get("tech_score", 0)
                    res["final_score"] = reranker_score + tech_score * SCALE_FACTOR
                else:
                    res["final_score"] = reranker_score

            # final_score 기준 정렬 (탈락 없이 전체 정렬)
            all_results.sort(key=lambda x: x["final_score"], reverse=True)

            processed_documents = []
            for res in all_results:
                meta = res.get("metadata", {})

                processed_documents.append({
                    "id":             res.get("id", ""),
                    "content":        res.get("content") or res.get("document", ""),
                    "title":          meta.get("title", "제목 없음"),
                    "type":           meta.get("type", "document"),
                    "source":         meta.get("source", ""),
                    "language":       meta.get("language", "ko"),
                    "created_at":     meta.get("created_at", get_utc_now()),
                    "status":         meta.get("status", "processed"),
                    "notion_url":     meta.get("notion_url", ""),
                    "chroma_id":      meta.get("chroma_id", ""),
                    "error":          meta.get("error", ""),
                    "user_edited":    meta.get("user_edited", False),
                    "tags":           meta.get("tags", ""),
                    "importance_score": meta.get("importance_score", 0),
                    "score":          res.get("final_score", 0),
                    "reranker_score": res.get("reranker_score", 0),
                    "tech_score":     meta.get("tech_score", 0),
                    "document_id":    meta.get("document_id", ""),
                    "filename":       meta.get("filename", ""),
                    "chunk_index":    meta.get("chunk_index", 0),
                    "upload_context": meta.get("upload_context", ""),
                    "room_id":        meta.get("room_id", ""),
                    "collection":     res.get("collection", ""),
                })

            # top_k에서만 자르기 (그 외 탈락 로직 없음)
            processed_documents = processed_documents[:top_k]

            top_score = processed_documents[0]["score"] if processed_documents else 0
            is_low_confidence = top_score < LOW_CONFIDENCE_THRESHOLD

            result = {
                "status": "success",
                "query":  query,
                "count":  len(processed_documents),
                "data":   processed_documents,
                "low_confidence": is_low_confidence,
                "error":  None,
            }

            confidence_label = "낮음" if is_low_confidence else "정상"
            print(
                f"[RAG Service] 완료 → {len(processed_documents)}개 반환 "
                f"(최고 final_score: {top_score:.4f}, 신뢰도: {confidence_label})"
            )
            return result

        except Exception as e:
            print(f"[RAG Service 에러]: {str(e)}")
            return {
                "status": "error",
                "query":  query,
                "count":  0,
                "data":   [],
                "low_confidence": True,
                "error":  f"RAG 파이프라인 장애: {str(e)}",
            }

    @staticmethod
    def retrieve_relevant_knowledge_sync(
        query: str,
        original_query: str = None,
        top_k: int = 5,
        relative_threshold: float = 0.5,
        filter: dict = None,
        question_type: str = "general_answer",
    ) -> dict:
        return RAGService.retrieve_relevant_knowledge(
            query=query,
            original_query=original_query,
            top_k=top_k,
            relative_threshold=relative_threshold,
            filter=filter,
            question_type=question_type,
        )


rag_service = RAGService()