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

SOURCE = "docker_docs"
CATEGORY = "infra"
CATEGORY_TAGS = ["인프라", "devops", "장애대응"]
SAVE_INTERVAL = 10

INCLUDE_PREFIXES = [
    "https://docs.docker.com/engine/",
    "https://docs.docker.com/build/",
    "https://docs.docker.com/compose/",
    "https://docs.docker.com/get-started/",
    "https://docs.docker.com/reference/dockerfile/",
    "https://docs.docker.com/reference/compose-file/",
    "https://docs.docker.com/reference/cli/docker/",
    "https://docs.docker.com/docker-hub/",
    "https://docs.docker.com/scout/",
]
EXCLUDE_PATTERNS = [
    "/reference/cli/docker/container/ls",
    "/reference/cli/docker/image/ls",
    "changelog",
    "release-notes",
]


def get_urls_from_sitemap() -> list[str]:
    """사이트맵에서 도커 공식문서 URL 수집."""
    sitemap_urls = [
        "https://docs.docker.com/sitemap.xml",
    ]
    print("사이트맵 수집 중...")

    all_urls = []
    for sitemap_url in sitemap_urls:
        try:
            response = requests.get(sitemap_url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "xml")

            # 서브 사이트맵 확인
            sitemaps = [loc.text for loc in soup.find_all("loc") if "sitemap" in loc.text]
            if sitemaps:
                for sub in sitemaps:
                    try:
                        resp = requests.get(sub, headers=HEADERS, timeout=30)
                        sub_soup = BeautifulSoup(resp.text, "xml")
                        urls = [loc.text for loc in sub_soup.find_all("loc")]
                        all_urls.extend(urls)
                        time.sleep(0.3)
                    except Exception as e:
                        print(f"[서브 사이트맵 오류] {sub}: {e}")
            else:
                urls = [loc.text for loc in soup.find_all("loc")]
                all_urls.extend(urls)

        except Exception as e:
            print(f"[사이트맵 오류] {sitemap_url}: {e}")

    # 필터링
    filtered = []
    for url in all_urls:
        if not any(url.startswith(prefix) for prefix in INCLUDE_PREFIXES):
            continue
        if any(exc in url for exc in EXCLUDE_PATTERNS):
            continue
        filtered.append(url)

    print(f"필터링 후 URL: {len(filtered)}개")
    return list(set(filtered))


FALLBACK_URLS = [
    "https://docs.docker.com/get-started/docker-overview/",
    "https://docs.docker.com/reference/dockerfile/",
    "https://docs.docker.com/build/building/best-practices/",
    "https://docs.docker.com/build/building/multi-stage/",
    "https://docs.docker.com/build/building/context/",
    "https://docs.docker.com/build/cache/",
    "https://docs.docker.com/engine/containers/run/",
    "https://docs.docker.com/engine/containers/resource_constraints/",
    "https://docs.docker.com/engine/containers/start-containers-automatically/",
    "https://docs.docker.com/engine/logging/configure/",
    "https://docs.docker.com/engine/storage/volumes/",
    "https://docs.docker.com/engine/storage/bind-mounts/",
    "https://docs.docker.com/engine/storage/drivers/",
    "https://docs.docker.com/engine/network/",
    "https://docs.docker.com/engine/network/drivers/bridge/",
    "https://docs.docker.com/engine/network/drivers/host/",
    "https://docs.docker.com/engine/network/drivers/overlay/",
    "https://docs.docker.com/compose/intro/features-uses/",
    "https://docs.docker.com/reference/compose-file/",
    "https://docs.docker.com/compose/how-tos/networking/",
    "https://docs.docker.com/compose/how-tos/environment-variables/",
    "https://docs.docker.com/compose/how-tos/profiles/",
    "https://docs.docker.com/compose/how-tos/startup-order/",
    "https://docs.docker.com/compose/how-tos/scaling/",
    "https://docs.docker.com/engine/security/",
    "https://docs.docker.com/engine/security/rootless/",
    "https://docs.docker.com/engine/manage-resources/pruning/",
    "https://docs.docker.com/build/buildkit/",
    "https://docs.docker.com/build/building/multi-platform/",
    "https://docs.docker.com/build/ci/github-actions/",
    "https://docs.docker.com/engine/swarm/",
    "https://docs.docker.com/engine/swarm/services/",
    "https://docs.docker.com/reference/cli/docker/container/run/",
    "https://docs.docker.com/reference/cli/docker/container/logs/",
    "https://docs.docker.com/reference/cli/docker/container/inspect/",
    "https://docs.docker.com/reference/cli/docker/container/exec/",
    "https://docs.docker.com/reference/cli/docker/container/stats/",
    "https://docs.docker.com/reference/cli/docker/container/update/",
    "https://docs.docker.com/reference/dockerfile/#healthcheck",
    "https://docs.docker.com/engine/network/drivers/macvlan/",
]


def crawl_docker_page(url: str) -> dict | None:
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        h1 = soup.find("h1")
        page_title = h1.get_text(strip=True) if h1 else url.split("/")[-2] or "문서"

        content_div = (
            soup.find("main") or
            soup.find("div", {"class": "content"}) or
            soup.find("article")
        )
        if not content_div:
            return None

        for tag in content_div.find_all(["script", "style", "nav", "footer", "aside"]):
            tag.decompose()

        text = content_div.get_text(separator="\n", strip=True)

        if len(text) < 200:
            return None

        full_title = f"도커 - {page_title}"

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
            "tags": ["도커", "공식문서", "docker"] + CATEGORY_TAGS,
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
    print("\n[docker 크롤러] 시작...\n")
    results = []
    existing_urls = set()
    output_path = os.path.join(OUTPUT_DIR, "docker_docs.json")

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
        doc = crawl_docker_page(url)
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