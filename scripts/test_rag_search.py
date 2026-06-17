# scripts/test_rag_search.py
# 적재된 knowledge_collection에 대해 실제 질문으로 검색 테스트
# 확인 목적:
#   1. _select_collections()가 의도한 컬렉션을 잘 고르는지
#   2. reranker_score 분포가 어느 범위인지 (SCALE_FACTOR 검증용)
#   3. final_score 정렬 후 상위 문서가 질문과 실제로 관련 있는지
#   4. 크롤링 데이터 자체가 부실해서 안 나오는 건지,
#      검색/정렬 로직 문제로 안 나오는 건지 구분

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from backend.services.rag_service import (
    rag_service,
    _select_collections,
)

# ── 테스트 질문 세트 ──────────────────────────────────────────
# question_type은 실제 classify_for_graph()가 줄 값으로 가정
TEST_CASES = [
    # (query, question_type, 기대 컬렉션 — 육안 확인용)
    ("쿠버네티스 파드가 OOM으로 죽었는데 어떻게 해결해", "knowledge_search", "knowledge"),
    ("도커 컨테이너 재시작 정책 어떻게 설정해", "knowledge_search", "knowledge"),
    ("깃허브 액션 워크플로우가 멈췄는데 재실행하려면", "knowledge_search", "knowledge"),
    ("Dockerfile 멀티스테이지 빌드 어떻게 하는거야", "knowledge_search", "knowledge"),
    ("저번 회의에서 나온 에러 해결방안 알려줘", "knowledge_search", "meeting+knowledge"),
    ("도커 네트워크 종류 알려줘", "knowledge_search", "knowledge"),
    ("쿠버네티스 롤링 업데이트 하는 방법", "knowledge_search", "knowledge"),
    ("회의록에서 할 일 추출해줘", "task_from_rag", "meeting"),
]


def run_test(query: str, question_type: str, expected: str):
    print("=" * 70)
    print(f"질문: {query}")
    print(f"question_type: {question_type} (기대 컬렉션 힌트: {expected})")
    print("-" * 70)

    # 1. 컬렉션 선택 확인
    collections = _select_collections(question_type=question_type, query=query, filter=None)
    print(f"[1] 선택된 컬렉션: {collections}")

    # 2. 실제 검색 실행
    result = rag_service.retrieve_relevant_knowledge(
        query=query,
        top_k=5,
        relative_threshold=0.3,  # 테스트 시에는 느슨하게 (원래보다 더 보기 위함)
        filter=None,
        question_type=question_type,
    )

    print(f"[2] 검색 결과 status: {result.get('status')}, count: {result.get('count')}")

    if result.get("count", 0) == 0:
        print("    → 결과 없음 (relative_threshold 또는 min_absolute_bound에 걸렸을 가능성)")
        print()
        return

    # 3. 상위 결과 출력 (reranker_score, tech_score, final_score 분포 확인용)
    print(f"[3] 상위 {len(result['data'])}개 결과:")
    for i, doc in enumerate(result["data"], 1):
        print(
            f"    {i}. [{doc.get('collection')}] {doc.get('title')}\n"
            f"       final_score={doc.get('score'):.4f} "
            f"reranker_score={doc.get('reranker_score'):.4f} "
            f"tech_score={doc.get('tech_score')}"
        )
        content_preview = (doc.get("content") or "")[:80].replace("\n", " ")
        print(f"       content 미리보기: {content_preview}...")

    print()


def main():
    print("RAG 검색 테스트 시작\n")
    for query, qtype, expected in TEST_CASES:
        try:
            run_test(query, qtype, expected)
        except Exception as e:
            print(f"[에러] 질문 '{query}' 처리 중 실패: {e}\n")

    print("=" * 70)
    print("테스트 완료")
    print(
        "\n[확인 포인트]\n"
        "1. 선택된 컬렉션이 기대와 다르면 → _select_collections() 신호어 보완 필요\n"
        "2. count=0이 자주 나오면 → relative_threshold/min_absolute_bound가 너무 엄격하거나\n"
        "   reranker_score 자체가 낮게 나오는 것 (크롤링 데이터 임베딩 적합도 문제 가능성)\n"
        "3. reranker_score가 항목별로 거의 차이 없으면 (예: 전부 0.5~0.6) →\n"
        "   reranker가 변별을 잘 못 하는 것, SCALE_FACTOR 재조정 필요\n"
        "4. 상위 문서가 질문과 무관하면 → 크롤링 데이터 자체의 품질/커버리지 문제\n"
        "   (예: '도커 네트워크' 질문에 k8s 문서가 1위로 오면 데이터/임베딩 모델 점검 필요)\n"
    )


if __name__ == "__main__":
    main()