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

# 신호어 (의도분류와 컬렉션 선택 양쪽에서 참고할 공통 키워드)
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


def is_rag_result_relevant(rag_result: dict, min_score: float = 0.5) -> bool:
    if rag_result.get("status") != "success":
        return False
    if rag_result.get("count", 0) == 0:
        return False
    data = rag_result.get("data", [])
    if not data:
        return False
    top_score = data[0].get("score", 0)
    return top_score >= min_score


def _has_specific_document_filter(filter: dict | None) -> bool:
    if not filter:
        return False
    return bool(filter.get("document_id") or filter.get("filename"))


# ── 컬렉션 선택 (복수 반환) ───────────────────────────────────
def _select_collections(
    question_type: str,
    query: str = "",
    filter: dict | None = None,
) -> list[str]:
    """
    question_type(3개: task_from_rag, notion_save, knowledge_search)과
    query 신호어를 함께 보고 검색할 컬렉션 리스트 반환.

    설계 원칙:
    - 신호어를 먼저 판단 (실제 사용자 발화 기준, 더 정확)
    - question_type은 "최소 보장" 힌트로만 추가
      (task_from_rag → meeting 최소 보장,
       나머지는 신호어만으로 판단)
    - 신호어가 하나도 안 잡히면 전체 컬렉션 검색 (정보 손실 방지)
    """
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

    # question_type을 "최소 보장" 힌트로 추가
    # (신호어가 못 잡아도 question_type이 확실하면 강제로 포함)
    if question_type == "task_from_rag":
        targets.add(MEETING_COLLECTION)

    # task_from_memory, general_answer는 여기 도달하지 않음
    # (need_rag=False라서 retrieve_relevant_knowledge 자체가 호출 안 됨)
    # notion_save, knowledge_search는 신호어 판단에만 의존

    return list(targets) if targets else all_collections


class RAGService:

    @staticmethod
    def retrieve_relevant_knowledge(
        query: str,
        original_query: str = None,
        top_k: int = 5,
        relative_threshold: float = 0.5,
        filter: dict = None,
        question_type: str = "general_answer",
    ):
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

            all_results.sort(key=lambda x: x["final_score"], reverse=True)

            max_score = all_results[0]["final_score"]
            min_absolute_bound = 0.1
            processed_documents = []

            for res in all_results:
                relative_ratio = res["final_score"] / max_score if max_score > 0 else 0

                if (
                    res["final_score"] < min_absolute_bound
                    or relative_ratio < relative_threshold
                ):
                    print(f"[탈락] final_score: {res['final_score']:.4f}")
                    continue

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

            processed_documents = processed_documents[:top_k]

            result = {
                "status": "success",
                "query":  query,
                "count":  len(processed_documents),
                "data":   processed_documents,
                "error":  None,
            }

            if _has_specific_document_filter(filter):
                print(f"[RAG Service] 특정 문서 검색 완료 → {len(processed_documents)}개 반환")
                return result

            if not is_rag_result_relevant(result):
                print("[RAG Service] 품질 미달 → 빈 결과 반환")
                return {
                    "status": "success",
                    "query":  query,
                    "count":  0,
                    "data":   [],
                    "error":  None,
                }

            print(f"[RAG Service] 완료 → {len(processed_documents)}개 반환 (최고 final_score: {max_score:.4f})")
            return result

        except Exception as e:
            print(f"[RAG Service 에러]: {str(e)}")
            return {
                "status": "error",
                "query":  query,
                "count":  0,
                "data":   [],
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