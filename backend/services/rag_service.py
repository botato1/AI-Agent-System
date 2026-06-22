# backend/services/rag_service.py
import re
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
CANDIDATE_K  = 40
SCALE_FACTOR = 0.0005

# 8개 질문 실측 기준: 관련있음 0.7~0.99, 무관 0.3 미만
LOW_CONFIDENCE_THRESHOLD = 0.3

MEETING_SIGNALS = [
    "회의록", "회의", "저번에", "저번", "말했던", "논의했던", "논의",
    "액션아이템", "참석자", "지난번", "지난", "미팅",
]
DOCUMENT_SIGNALS = [
    "문서", "파일", "보냈던", "올린", "자료",
    "보고서", "pdf", "첨부",
]
KNOWLEDGE_SIGNALS = [
    # 일반 기술 키워드
    "에러", "오류", "방법", "설치", "설정", "코드", "구현", "사용",
    "배포", "파이프라인", "빌드", "실행", "연결", "적용", "구성",
    # 도커
    "도커", "docker", "dockerfile", "컨테이너", "container",
    "이미지", "image", "compose", "레지스트리",
    # 쿠버네티스
    "쿠버", "kubernetes", "k8s", "pod", "파드", "deployment",
    "서비스", "ingress", "helm", "클러스터", "노드",
    # 깃허브
    "깃허브", "github", "actions", "워크플로", "workflow",
    "ci", "cd", "cicd", "브랜치", "커밋", "push", "pull request",
    # 기타 기술
    "api", "서버", "네트워크", "network", "포트", "port",
    "데이터베이스", "db", "sql", "redis", "nginx",
    "로그", "모니터링", "장애", "디버그", "테스트",
]

# 컬렉션 이름 → 결과 키 매핑
COL_KEY_MAP = {
    MEETING_COLLECTION:   "meeting",
    DOCUMENT_COLLECTION:  "document",
    KNOWLEDGE_COLLECTION: "knowledge",
}


def get_utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _has_specific_document_filter(filter: dict | None) -> bool:
    if not filter:
        return False
    return bool(filter.get("document_id") or filter.get("filename"))


def _refine_query_for_knowledge(query: str) -> str:
    """
    knowledge_collection 검색용 쿼리 정제.
    회의/문서 관련 맥락 표현을 정규식 패턴으로 제거해서 기술 내용만 남긴다.

    예: "저번 회의에서 나온 에러 해결방안 알려줘" -> "에러 해결방안 알려줘"
    예: "저번 미팅에서 논의한 쿠버네티스 배포 문제" -> "쿠버네티스 배포 문제"

    접근: MEETING_SIGNALS/DOCUMENT_SIGNALS를 단순 제거하는 대신,
    "회의/미팅/저번 + 조사/어미" 패턴을 한 덩어리로 잡아서 제거.
    이 방식이 "한", "된" 같은 어미 찌꺼기를 남기지 않아 더 안전함.

    제거 후 결과가 너무 짧아지면(5글자 미만) 원문을 그대로 반환한다.
    """
    # 회의 맥락 패턴: "저번/지난 + (회의/미팅 등) + 조사어미" 형태를 통째로 제거
    # 각 패턴을 명시적으로 정의 (과잉 제거 방지)
    meeting_patterns = [
        r"저번\s*(?:회의록?|미팅|번|에)?\s*(?:에서|에서의|의|에게|때|으로부터|로부터)?",
        r"지난\s*(?:번|회의록?|미팅|번의)?\s*(?:에서|에서의|의|에게|때|으로부터|로부터)?",
        r"(?:회의록?|미팅)\s*(?:에서|에서의|에|의|때|에서도|에서부터)?",
        r"(?:논의|말|얘기)(?:했던|한|된|할)\s*",
        r"액션\s*아이템\s*",
        r"참석자\s*(?:들?의|들?)?\s*",
    ]
    document_patterns = [
        r"(?:문서|파일|자료|보고서|첨부)\s*(?:에서|에서의|에|의|를|을|로|으로)?",
        r"(?:보냈던|올린|올렸던)\s*",
        r"pdf\s*(?:에서|에서의|에|의|를|을)?",
    ]

    refined = query
    for pattern in meeting_patterns + document_patterns:
        refined = re.sub(pattern, " ", refined, flags=re.IGNORECASE)

    refined = re.sub(r"\s+", " ", refined).strip()

    if len(refined) < 5:
        return query
    return refined


def _select_collections_with_queries(
    question_type: str,
    query: str = "",
    filter: dict | None = None,
) -> list[tuple[str, str]]:
    """
    검색할 컬렉션과 그 컬렉션에 맞는 정제된 쿼리를 함께 반환한다.
    반환 형식: [(collection_name, query_for_this_collection), ...]

    컬렉션별 쿼리 정제 규칙:
    - meeting_collection  -> 원문 그대로 (회의 맥락 단어가 오히려 도움)
    - document_collection -> 원문 그대로 (사용자가 직접 가리킨 문서)
    - knowledge_collection -> MEETING_SIGNALS/DOCUMENT_SIGNALS 제거
                              (기술 내용만 남겨서 임베딩 정확도 향상)

    예: "저번 회의에서 나온 에러 해결방안 알려줘"
        meeting_collection   -> "저번 회의에서 나온 에러 해결방안 알려줘" (원문)
        knowledge_collection -> "에러 해결방안 알려줘" (정제)
    """
    all_collections = [MEETING_COLLECTION, DOCUMENT_COLLECTION, KNOWLEDGE_COLLECTION]

    if _has_specific_document_filter(filter):
        return [(col, query) for col in all_collections]

    has_meeting   = any(s in query for s in MEETING_SIGNALS)
    has_document  = any(s in query for s in DOCUMENT_SIGNALS)
    has_knowledge = any(s in query for s in KNOWLEDGE_SIGNALS)

    targets = set()
    if has_meeting:   targets.add(MEETING_COLLECTION)
    if has_document:  targets.add(DOCUMENT_COLLECTION)
    if has_knowledge: targets.add(KNOWLEDGE_COLLECTION)

    if question_type == "task_from_rag":
        targets.add(MEETING_COLLECTION)

    if not targets:
        targets = set(all_collections)

    knowledge_query = _refine_query_for_knowledge(query)

    result = []
    for col in targets:
        if col == KNOWLEDGE_COLLECTION:
            result.append((col, knowledge_query))
        else:
            result.append((col, query))

    return result


def _select_collections(
    question_type: str,
    query: str = "",
    filter: dict | None = None,
) -> list[str]:
    """하위 호환성 유지용. 컬렉션 이름만 반환."""
    return [col for col, _ in _select_collections_with_queries(
        question_type=question_type,
        query=query,
        filter=filter,
    )]


def _apply_final_score(results: list) -> list:
    """reranker_score + tech_score 보정 → final_score 계산 후 정렬."""
    for res in results:
        reranker_score = res.get("reranker_score", 0.0)
        if res.get("collection") == KNOWLEDGE_COLLECTION:
            tech_score = res.get("metadata", {}).get("tech_score", 0)
            res["final_score"] = reranker_score + tech_score * SCALE_FACTOR
        else:
            res["final_score"] = reranker_score

    results.sort(key=lambda x: x["final_score"], reverse=True)
    return results


def _format_documents(raw_results: list) -> list:
    """raw_results → 최종 반환 포맷으로 변환."""
    processed = []
    for res in raw_results:
        meta = res.get("metadata", {})
        processed.append({
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
    return processed


def _make_collection_result(documents: list, top_k: int) -> dict:
    """단일 컬렉션의 처리 결과를 신뢰도 포함해서 반환."""
    sliced = documents[:top_k]
    top_score = sliced[0]["score"] if sliced else 0.0
    return {
        "count": len(sliced),
        "low_confidence": top_score < LOW_CONFIDENCE_THRESHOLD,
        "top_score": round(top_score, 4),
        "data": sliced,
    }


def _empty_collection_result() -> dict:
    return {"count": 0, "low_confidence": True, "top_score": 0.0, "data": []}


class RAGService:

    @staticmethod
    def retrieve_relevant_knowledge(
        query: str,
        original_query: str = None,
        top_k: int = 5,
        relative_threshold: float = 0.5,  # 호환성 유지, 실제 필터링에 미사용
        filter: dict = None,
        question_type: str = "general_answer",
    ):
        """
        흐름:
        1. _select_collections()로 검색할 컬렉션(들) 결정
        2. 컬렉션별로 따로 하이브리드 검색 (CANDIDATE_K개씩)
        3. 컬렉션별로 따로 reranker 재평가
        4. final_score 계산 (knowledge만 tech_score 보정)
        5. 컬렉션별로 top_k 잘라서 신뢰도 판정 → collection_results에 담음
        6. 전체 합쳐서 점수 기준 정렬 → data (기존 호환성 유지)

        [수정 - 2026.06.22] 컬렉션별 분리 리팩토링
        기존: 모든 컬렉션 결과를 합쳐서 점수로만 정렬.
             "저번 회의에서 나온 에러 해결방안"처럼 회의록+지식 신호가 섞인 질문에서,
             meeting이 비어있을 때 무관한 knowledge 결과만 5개 나오는 혼란 발생.
        변경: 컬렉션별로 검색/리랭킹/신뢰도를 따로 계산해서 collection_results에 담음.
             ollama_client.py가 "회의록: 못 찾음 / 지식: 이렇게 설명" 형태로
             구분해서 답변 생성 가능. 기존 data/count/low_confidence는 그대로 유지.
        """
        print(f"[RAG Service] 쿼리: '{query}' / 타입: '{question_type}'")
        print(f"[RAG Service] filter: {filter}")

        try:
            collections_with_queries = _select_collections_with_queries(
                question_type=question_type,
                query=query,
                filter=filter,
            )
            collections = [col for col, _ in collections_with_queries]
            print(f"[RAG Service] 검색 컬렉션: {collections}")

            # 쿼리 정제 결과 로그
            for col, q in collections_with_queries:
                key = COL_KEY_MAP.get(col, col)
                if q != query:
                    print(f"[RAG Service] {key} 쿼리 정제: '{query}' -> '{q}'")

            # ── 컬렉션별 검색 + 리랭킹 + 포맷 변환 ──────────────
            per_col: dict[str, list] = {
                "meeting": [], "document": [], "knowledge": []
            }
            seen_ids: set = set()

            for col, col_query in collections_with_queries:
                raw = search_hybrid(
                    query_text=col_query,
                    top_k=CANDIDATE_K,
                    filter=filter,
                    collection_name=col,
                )

                # 중복 제거
                unique = [r for r in raw if r["id"] not in seen_ids]
                for r in unique:
                    seen_ids.add(r["id"])

                if not unique:
                    continue

                # 이 컬렉션만 따로 리랭킹
                unique = rerank_results(query, unique)
                # final_score 계산 + 정렬
                unique = _apply_final_score(unique)
                # 포맷 변환
                formatted = _format_documents(unique)

                key = COL_KEY_MAP.get(col, "knowledge")
                per_col[key].extend(formatted)

            # ── 컬렉션별 신뢰도 판정 ─────────────────────────────
            collection_results = {
                key: (
                    _make_collection_result(per_col[key], top_k)
                    if per_col[key]
                    else _empty_collection_result()
                )
                for key in ["meeting", "document", "knowledge"]
            }

            # ── 전체 합산 (기존 호환성) ───────────────────────────
            all_docs = []
            for key in ["meeting", "document", "knowledge"]:
                all_docs.extend(per_col[key])

            if not all_docs:
                return {
                    "status": "success",
                    "query": query,
                    "count": 0,
                    "data": [],
                    "low_confidence": True,
                    "collection_results": collection_results,
                    "searched_collections": [COL_KEY_MAP.get(col, col) for col in collections],
                    "error": None,
                }

            all_docs.sort(key=lambda x: x["score"], reverse=True)
            top_documents = all_docs[:top_k]

            top_score = top_documents[0]["score"] if top_documents else 0
            is_low_confidence = top_score < LOW_CONFIDENCE_THRESHOLD

            result = {
                "status": "success",
                "query":  query,
                "count":  len(top_documents),
                "data":   top_documents,
                "low_confidence": is_low_confidence,
                "collection_results": collection_results,
                "searched_collections": [COL_KEY_MAP.get(col, col) for col in collections],
                "error":  None,
            }

            confidence_label = "낮음" if is_low_confidence else "정상"
            cr = collection_results
            print(
                f"[RAG Service] 완료 → {len(top_documents)}개 반환 "
                f"(최고 final_score: {top_score:.4f}, 신뢰도: {confidence_label})"
            )
            print(
                f"[RAG Service] 컬렉션별 → "
                f"meeting={cr['meeting']['count']}개"
                f"({'낮음' if cr['meeting']['low_confidence'] else '정상'}), "
                f"document={cr['document']['count']}개"
                f"({'낮음' if cr['document']['low_confidence'] else '정상'}), "
                f"knowledge={cr['knowledge']['count']}개"
                f"({'낮음' if cr['knowledge']['low_confidence'] else '정상'})"
            )
            return result

        except Exception as e:
            print(f"[RAG Service 에러]: {str(e)}")
            empty = _empty_collection_result()
            return {
                "status": "error",
                "query":  query,
                "count":  0,
                "data":   [],
                "low_confidence": True,
                "collection_results": {
                    "meeting": empty, "document": empty, "knowledge": empty,
                },
                "error": f"RAG 파이프라인 장애: {str(e)}",
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