# scripts/crawlers/validate_data.py
import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
KNOWLEDGE_DIR = os.path.join(BASE_DIR, "data", "knowledge")

REQUIRED_FIELDS = [
    "id", "title", "type", "category", "source", "content",
    "language", "created_at", "published_date", "tags",
    "tech_score", "keywords", "status", "upload_context", "url"
]


def validate_file(filepath: str):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"\n=== {os.path.basename(filepath)} ===")
    print(f"총 문서 수: {len(data)}")

    if not data:
        print("문서 없음")
        return

    missing_fields_count = 0
    tech_scores = []
    no_date_count = 0
    short_content_count = 0
    duplicate_url_count = 0
    category_counter = {}
    source_set = set()

    seen_urls = set()

    for doc in data:
        # 필수 필드 체크
        missing = [field for field in REQUIRED_FIELDS if field not in doc]
        if missing:
            missing_fields_count += 1
            print(f"  [필드 누락] {doc.get('title', 'unknown')}: {missing}")

        # tech_score 통계
        tech_scores.append(doc.get("tech_score", 0))

        # 날짜 없음
        if not doc.get("published_date"):
            no_date_count += 1

        # 너무 짧은 content
        content_len = len(doc.get("content", ""))
        if content_len < 200:
            short_content_count += 1

        # 중복 URL
        url = doc.get("url")
        if url:
            if url in seen_urls:
                duplicate_url_count += 1
            seen_urls.add(url)

        # 카테고리 분포
        category = doc.get("category", "unknown")
        category_counter[category] = category_counter.get(category, 0) + 1

        # source 종류
        source_set.add(doc.get("source", "unknown"))

    if tech_scores:
        sorted_scores = sorted(tech_scores)
        print(f"tech_score - 평균: {sum(tech_scores)/len(tech_scores):.1f}, "
              f"최소: {min(tech_scores)}, 최대: {max(tech_scores)}")

        # 상위 3개 / 하위 3개 제목
        scored_docs = sorted(data, key=lambda d: d.get("tech_score", 0), reverse=True)
        print("  상위 3개:")
        for d in scored_docs[:3]:
            print(f"    {d.get('tech_score')}점 - {d.get('title')}")
        print("  하위 3개:")
        for d in scored_docs[-3:]:
            print(f"    {d.get('tech_score')}점 - {d.get('title')}")

    print(f"카테고리 분포: {category_counter}")
    print(f"source 종류: {source_set}")
    print(f"날짜 없는 문서: {no_date_count}개")
    print(f"내용 200자 미만: {short_content_count}개")
    print(f"중복 URL: {duplicate_url_count}개")
    print(f"필드 누락 문서: {missing_fields_count}개")


def run():
    if not os.path.exists(KNOWLEDGE_DIR):
        print(f"폴더 없음: {KNOWLEDGE_DIR}")
        return

    files = [f for f in os.listdir(KNOWLEDGE_DIR) if f.endswith(".json")]

    if not files:
        print("검증할 JSON 파일이 없습니다.")
        return

    for filename in files:
        validate_file(os.path.join(KNOWLEDGE_DIR, filename))


if __name__ == "__main__":
    run()