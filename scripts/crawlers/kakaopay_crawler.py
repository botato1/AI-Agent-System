# scripts/crawlers/kakaopay_crawler.py
import os
import sys
import json
import time
import uuid
import re
from pathlib import Path
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from scripts.crawlers.score_utils import calculate_tech_score, is_within_years, detect_category

OUTPUT_DIR = os.path.join(BASE_DIR, "data", "knowledge")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


BLOG_URL = "https://tech.kakaopay.com"
SOURCE = "kakaopay_tech_blog"
MAX_AGE_YEARS = 2
SAVE_INTERVAL = 5
MAX_PAGES = 20

# 카카오페이 블로그 태그 목록 (실제 태그 기준)
TAGS = [
    "be", "fe", "ios", "kotlin", "data", "devops",
    "ai", "aws", "sre", "react", "spring-batch",
    "kubernetes", "sentry", "string", "slack",
    "devrel", "ifkakao", "ifkakao2022",
    "testcode", "google-cloud-next",
]


def get_article_links(page) -> list[str]:
    """태그별 페이지 순회로 링크 수집."""
    all_links = []

    # 메인 페이지에서 전체 글 목록 먼저 시도
    print("메인 페이지 수집 중...")
    for page_num in range(1, MAX_PAGES + 1):
        if page_num == 1:
            url = f"{BLOG_URL}"
        else:
            url = f"{BLOG_URL}?page={page_num}"

        try:
            page.goto(url, timeout=60000, wait_until="networkidle")
            time.sleep(2)

            links = page.eval_on_selector_all(
                "a",
                f"els => els.map(el => el.href).filter(h => h.startsWith('{BLOG_URL}/post/'))"
            )

            if not links:
                print(f"메인 페이지 {page_num} 링크 없음 → 태그별 수집으로 전환")
                break

            prev = len(set(all_links))
            all_links.extend(links)
            new = len(set(all_links)) - prev
            print(f"  메인 페이지 {page_num}: {len(links)}개 (신규 {new}개)")

            if new == 0:
                break

        except Exception as e:
            print(f"  [에러] {e}")
            break

    # 태그별 수집
    for tag in TAGS:
        print(f"\n[태그] {tag}")
        for page_num in range(1, MAX_PAGES + 1):
            if page_num == 1:
                url = f"{BLOG_URL}/tag/{tag}"
            else:
                url = f"{BLOG_URL}/tag/{tag}?page={page_num}"

            try:
                page.goto(url, timeout=60000, wait_until="networkidle")
                time.sleep(2)

                links = page.eval_on_selector_all(
                    "a",
                    f"els => els.map(el => el.href).filter(h => h.startsWith('{BLOG_URL}/post/'))"
                )

                if not links:
                    break

                prev = len(set(all_links))
                all_links.extend(links)
                new = len(set(all_links)) - prev
                print(f"  페이지 {page_num}: {len(links)}개 (신규 {new}개)")

                if new == 0:
                    break

            except Exception as e:
                print(f"  [에러] {e}")
                break

    return list(set(all_links))


def extract_date(page) -> str | None:
    try:
        meta_date = page.get_attribute('meta[property="article:published_time"]', "content")
        if meta_date:
            return meta_date
    except Exception:
        pass
    try:
        time_el = page.get_attribute("time", "datetime")
        if time_el:
            return time_el
    except Exception:
        pass
    try:
        # "2024. 3. 18" 형식
        text = page.inner_text("body")
        match = re.search(r"\d{4}\.\s*\d{1,2}\.\s*\d{1,2}", text)
        return match.group(0) if match else None
    except Exception:
        return None


def crawl_article(page, url: str) -> dict | None:
    try:
        page.goto(url, timeout=60000, wait_until="networkidle")
        time.sleep(1)

        title = page.title().replace(" | 카카오페이 기술 블로그", "").replace(" - 카카오페이 기술 블로그", "").strip()

        content = None
        for selector in ["article", ".post-content", ".content", "main"]:
            try:
                content = page.eval_on_selector(selector, "el => el.innerText")
                if content and len(content) >= 200:
                    break
            except Exception:
                continue

        if not content or len(content) < 200:
            print(f"[스킵] 내용 너무 짧음: {title}")
            return None

        date_str = extract_date(page)

        if not is_within_years(date_str, MAX_AGE_YEARS):
            print(f"[스킵] 오래된 문서 ({date_str}): {title}")
            return None

        tech_score, keywords_found = calculate_tech_score(
            title=title,
            content=content,
            date_str=date_str,
            source=SOURCE,
        )

        category, category_tags = detect_category(title, content)

        return {
            "id": str(uuid.uuid4()),
            "title": f"카카오페이 기술 블로그 - {title}",
            "type": "document",
            "category": category,
            "source": SOURCE,
            "content": content,
            "language": "ko",
            "created_at": get_utc_now(),
            "published_date": date_str,
            "tags": ["카카오페이", "기술블로그"] + category_tags,
            "tech_score": tech_score,
            "keywords": keywords_found,
            "status": "processed",
            "upload_context": "knowledge",
            "url": url,
        }

    except Exception as e:
        print(f"[에러] {url}: {e}")
        return None


def run():
    print("\n[카카오페이 기술 블로그 크롤러] 시작...\n")
    results = []
    existing_urls = set()
    output_path = os.path.join(OUTPUT_DIR, "kakaopay_blog.json")

    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                if isinstance(old_data, list):
                    results.extend(old_data)
                    existing_urls = {doc["url"] for doc in old_data if "url" in doc}
            print(f"기존 저장 파일 발견: {len(existing_urls)}개 스킵 목록 등록 완료")
        except Exception as e:
            print(f"기존 파일 로드 오류 (새로 생성): {e}")

    def save():
        tmp_path = output_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, output_path)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
        )

        print("아티클 링크 수집 중...")
        links = get_article_links(page)

        new_links = [url for url in links if url not in existing_urls]
        print(f"\n전체 링크: {len(links)}개 | 새로 크롤링: {len(new_links)}개\n")

        if not new_links:
            print("새로운 아티클 없음 → 종료")
            browser.close()
            return

        new_count = 0
        for url in new_links:
            print(f"크롤링 중: {url}")
            doc = crawl_article(page, url)
            if doc:
                results.append(doc)
                new_count += 1
                print(f"완료: {doc['title']} ({len(doc['content'])}자) | tech_score: {doc['tech_score']} | 카테고리: {doc['category']} | 날짜: {doc['published_date']}")

                if new_count % SAVE_INTERVAL == 0:
                    save()
                    print(f"[중간 저장] {new_count}개 처리됨")

            time.sleep(1)

        browser.close()

    save()
    print(f"\n[완료] 최종 {len(results)}개 아티클 저장 → {output_path}")


if __name__ == "__main__":
    run()