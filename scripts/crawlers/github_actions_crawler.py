import os
import sys
import json
import time
import uuid
import requests
from pathlib import Path
from datetime import datetime, timezone
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from scripts.crawlers.score_utils import calculate_tech_score, detect_language

OUTPUT_DIR = os.path.join(BASE_DIR, "data", "knowledge")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

SOURCE = "github_actions_docs"
CATEGORY = "infra"
CATEGORY_TAGS = ["인프라", "devops", "장애대응"]
SAVE_INTERVAL = 10

INCLUDE_PREFIX = "https://docs.github.com/ko/actions"
EXCLUDE_PATTERNS = [
    "changelog",
    "release-notes",
    "/rest/",
    "/graphql/",
]


def get_urls_from_sitemap() -> list[str]:
    """사이트맵에서 깃허브 액션 한국어 URL 수집."""
    sitemap_url = "https://docs.github.com/sitemap.xml"
    print(f"사이트맵 수집 중: {sitemap_url}")

    all_urls = []
    try:
        response = requests.get(sitemap_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "xml")

        sitemaps = [loc.text for loc in soup.find_all("loc") if "sitemap" in loc.text]
        print(f"서브 사이트맵 {len(sitemaps)}개 발견")

        # actions 관련 서브 사이트맵만 처리
        action_sitemaps = [s for s in sitemaps if "action" in s.lower() or "ko" in s.lower()]
        target_sitemaps = action_sitemaps if action_sitemaps else sitemaps[:10]

        for sub in target_sitemaps:
            try:
                resp = requests.get(sub, headers=HEADERS, timeout=30)
                sub_soup = BeautifulSoup(resp.text, "xml")
                urls = [loc.text for loc in sub_soup.find_all("loc")]
                all_urls.extend(urls)
                time.sleep(0.3)
            except Exception as e:
                print(f"[서브 사이트맵 오류] {sub}: {e}")

        if not all_urls:
            urls = [loc.text for loc in soup.find_all("loc") if not "sitemap" in loc.text]
            all_urls.extend(urls)

    except Exception as e:
        print(f"[사이트맵 오류] {e}")

    filtered = [
        url for url in all_urls
        if url.startswith(INCLUDE_PREFIX)
        and not any(exc in url for exc in EXCLUDE_PATTERNS)
    ]

    print(f"필터링 후 URL: {len(filtered)}개")
    return list(set(filtered))


FALLBACK_URLS = [
    # 기본 개념
    "https://docs.github.com/ko/actions/about-github-actions/understanding-github-actions",
    "https://docs.github.com/ko/actions/writing-workflows/workflow-syntax-for-github-actions",
    "https://docs.github.com/ko/actions/writing-workflows/choosing-what-your-workflow-does/using-jobs-in-a-workflow",
    "https://docs.github.com/ko/actions/writing-workflows/choosing-what-your-workflow-does/store-information-in-variables",
    # 트리거
    "https://docs.github.com/ko/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows",
    "https://docs.github.com/ko/actions/writing-workflows/choosing-when-your-workflow-runs/triggering-a-workflow",
    "https://docs.github.com/ko/actions/writing-workflows/choosing-when-your-workflow-runs/using-conditions-to-control-job-execution",
    # 보안
    "https://docs.github.com/ko/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions",
    "https://docs.github.com/ko/actions/security-for-github-actions/security-guides/automatic-token-authentication",
    "https://docs.github.com/ko/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions",
    "https://docs.github.com/ko/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect",
    # 재사용/구조화
    "https://docs.github.com/ko/actions/using-jobs/using-a-matrix-for-your-jobs",
    "https://docs.github.com/ko/actions/sharing-automations/reusing-workflows",
    "https://docs.github.com/ko/actions/sharing-automations/creating-actions/creating-a-composite-action",
    "https://docs.github.com/ko/actions/using-jobs/using-concurrency",
    "https://docs.github.com/ko/actions/writing-workflows/choosing-what-your-workflow-does/passing-information-between-jobs",
    # 배포
    "https://docs.github.com/ko/actions/deployment/targeting-different-environments/using-environments-for-deployment",
    "https://docs.github.com/ko/actions/use-cases-and-examples/publishing-packages/publishing-docker-images",
    "https://docs.github.com/ko/actions/use-cases-and-examples/deploying/deploying-to-google-kubernetes-engine",
    # 캐시/아티팩트
    "https://docs.github.com/ko/actions/writing-workflows/choosing-what-your-workflow-does/caching-dependencies-to-speed-up-workflows",
    "https://docs.github.com/ko/actions/writing-workflows/choosing-what-your-workflow-does/storing-and-sharing-data-from-a-workflow",
    # 러너
    "https://docs.github.com/ko/actions/hosting-your-own-runners/managing-self-hosted-runners/about-self-hosted-runners",
    "https://docs.github.com/ko/actions/hosting-your-own-runners/managing-self-hosted-runners-with-actions-runner-controller/about-actions-runner-controller",
    # 모니터링/디버깅
    "https://docs.github.com/ko/actions/monitoring-and-troubleshooting-workflows/troubleshooting-workflows/enabling-debug-logging",
    "https://docs.github.com/ko/actions/managing-workflow-runs-and-deployments/managing-workflow-runs/re-running-workflows-and-jobs",
    "https://docs.github.com/ko/actions/monitoring-and-troubleshooting-workflows/monitoring-workflows/adding-a-workflow-status-badge",
    "https://docs.github.com/ko/actions/managing-workflow-runs-and-deployments/managing-workflow-runs/canceling-a-workflow",
    # 컨테이너
    "https://docs.github.com/ko/actions/writing-workflows/choosing-where-your-workflow-runs/running-jobs-in-a-container",
    # 언어별 CI
    "https://docs.github.com/ko/actions/use-cases-and-examples/building-and-testing/building-and-testing-nodejs",
    "https://docs.github.com/ko/actions/use-cases-and-examples/building-and-testing/building-and-testing-python",
    "https://docs.github.com/ko/actions/use-cases-and-examples/building-and-testing/building-and-testing-java-with-maven",
    "https://docs.github.com/ko/actions/use-cases-and-examples/building-and-testing/building-and-testing-go",
    "https://docs.github.com/ko/actions/use-cases-and-examples/building-and-testing/building-and-testing-ruby",
    # 추가 배포
    "https://docs.github.com/ko/actions/use-cases-and-examples/deploying/deploying-to-amazon-elastic-container-service",
    "https://docs.github.com/ko/actions/use-cases-and-examples/deploying/deploying-to-azure-kubernetes-service",
    # 액션 만들기
    "https://docs.github.com/ko/actions/sharing-automations/creating-actions/about-custom-actions",
    "https://docs.github.com/ko/actions/sharing-automations/creating-actions/creating-a-javascript-action",
    "https://docs.github.com/ko/actions/sharing-automations/creating-actions/creating-a-docker-container-action",
    "https://docs.github.com/ko/actions/sharing-automations/creating-actions/metadata-syntax-for-github-actions",
    # 추가 개념
    "https://docs.github.com/ko/actions/writing-workflows/choosing-what-your-workflow-does/workflow-commands-for-github-actions",
    "https://docs.github.com/ko/actions/writing-workflows/choosing-what-your-workflow-does/controlling-permissions-for-github_token",
    "https://docs.github.com/ko/actions/using-jobs/using-environments-for-jobs",
    "https://docs.github.com/ko/actions/writing-workflows/choosing-what-your-workflow-does/evaluate-expressions-in-workflows-and-actions",
    "https://docs.github.com/ko/actions/writing-workflows/choosing-what-your-workflow-does/contexts",
]


def crawl_github_actions_page(url: str) -> dict | None:
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        h1 = soup.find("h1")
        page_title = h1.get_text(strip=True) if h1 else url.split("/")[-1] or "문서"

        content_div = (
            soup.find("div", {"class": "article-grid-body"}) or
            soup.find("main") or
            soup.find("article")
        )
        if not content_div:
            return None

        for tag in content_div.find_all(["script", "style", "nav", "footer", "aside"]):
            tag.decompose()

        text = content_div.get_text(separator="\n", strip=True)

        if len(text) < 200:
            return None

        full_title = f"깃허브 Actions - {page_title}"

        tech_score, keywords_found = calculate_tech_score(
            title=full_title,
            content=text,
            date_str=None,
            source=SOURCE,
        )

        return {
            "id": str(uuid.uuid4()),
            "title": full_title,
            "type": "document",
            "category": CATEGORY,
            "source": SOURCE,
            "content": text,
            "language": detect_language(text),
            "created_at": get_utc_now(),
            "published_date": None,
            "tags": ["깃허브", "Actions", "CI/CD", "공식문서"] + CATEGORY_TAGS,
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
    print("\n[GitHub Actions 크롤러] 시작...\n")
    results = []
    existing_urls = set()
    output_path = os.path.join(OUTPUT_DIR, "github_actions_docs.json")

    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                if isinstance(old_data, list):
                    results.extend(old_data)
                    existing_urls = {doc["url"] for doc in old_data if "url" in doc}
            print(f"기존 저장 파일 발견: {len(existing_urls)}개 스킵 목록 등록 완료")
        except Exception as e:
            print(f"기존 파일 로드 오류: {e}")

    def save():
        tmp_path = output_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, output_path)

    urls = get_urls_from_sitemap()

    if not urls:
        print("사이트맵 실패 → 폴백 URL 사용")
        urls = FALLBACK_URLS

    new_urls = [url for url in urls if url not in existing_urls]
    print(f"\n전체 URL: {len(urls)}개 | 새로 크롤링: {len(new_urls)}개\n")

    if not new_urls:
        print("새로운 문서 없음 → 종료")
        return

    new_count = 0
    for url in new_urls:
        print(f"크롤링 중: {url}")
        doc = crawl_github_actions_page(url)
        if doc:
            results.append(doc)
            new_count += 1
            print(f"완료: {doc['title']} ({len(doc['content'])}자) | tech_score: {doc['tech_score']}")

            if new_count % SAVE_INTERVAL == 0:
                save()
                print(f"[중간 저장] {new_count}개 처리됨")
        time.sleep(0.5)

    save()
    print(f"\n[완료] 최종 {len(results)}개 문서 저장 → {output_path}")


if __name__ == "__main__":
    run()