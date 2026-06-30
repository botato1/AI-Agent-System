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

from scripts.crawlers.score_utils import calculate_tech_score

OUTPUT_DIR = os.path.join(BASE_DIR, "data", "knowledge")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

SOURCE = "kubernetes_docs"
CATEGORY = "infra"
CATEGORY_TAGS = ["인프라", "devops", "장애대응"]
SAVE_INTERVAL = 10

# 사이트맵에서 수집할 경로 필터
# /ko/docs/ 하위만 가져오되, 불필요한 경로 제외
INCLUDE_PREFIX = "https://kubernetes.io/ko/docs/"
EXCLUDE_PATTERNS = [
    "/ko/docs/reference/generated/",  # 자동생성 API 레퍼런스 (너무 많고 노이즈)
    "/ko/docs/reference/kubernetes-api/",  # API 스펙 (너무 세분화)
]


def get_urls_from_sitemap() -> list[str]:
    """사이트맵에서 한국어 공식문서 URL 수집."""
    sitemap_url = "https://kubernetes.io/sitemap.xml"
    print(f"사이트맵 수집 중: {sitemap_url}")

    try:
        response = requests.get(sitemap_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "xml")

        # 서브 사이트맵 링크 찾기
        sitemaps = [loc.text for loc in soup.find_all("loc")]
        print(f"서브 사이트맵 {len(sitemaps)}개 발견")

        all_urls = []
        for sitemap in sitemaps:
            if "sitemap" not in sitemap:
                continue
            try:
                resp = requests.get(sitemap, headers=HEADERS, timeout=30)
                sub_soup = BeautifulSoup(resp.text, "xml")
                urls = [loc.text for loc in sub_soup.find_all("loc")]
                all_urls.extend(urls)
                time.sleep(0.5)
            except Exception as e:
                print(f"[서브 사이트맵 오류] {sitemap}: {e}")

        # 한국어 문서 URL만 필터링
        filtered = []
        for url in all_urls:
            if not url.startswith(INCLUDE_PREFIX):
                continue
            if any(exc in url for exc in EXCLUDE_PATTERNS):
                continue
            filtered.append(url)

        # 서브 사이트맵이 없으면 직접 파싱
        if not filtered:
            all_urls = [loc.text for loc in soup.find_all("loc")]
            filtered = [
                url for url in all_urls
                if url.startswith(INCLUDE_PREFIX)
                and not any(exc in url for exc in EXCLUDE_PATTERNS)
            ]

        print(f"필터링 후 URL: {len(filtered)}개")
        return list(set(filtered))

    except Exception as e:
        print(f"[사이트맵 오류] {e}")
        print("→ 하드코딩 URL 목록으로 폴백")
        return []


# 사이트맵 실패 시 폴백용 핵심 URL 목록
FALLBACK_URLS = [
    ("Pod",          "https://kubernetes.io/ko/docs/concepts/workloads/pods/"),
    ("Deployment",   "https://kubernetes.io/ko/docs/concepts/workloads/controllers/deployment/"),
    ("ReplicaSet",   "https://kubernetes.io/ko/docs/concepts/workloads/controllers/replicaset/"),
    ("StatefulSet",  "https://kubernetes.io/ko/docs/concepts/workloads/controllers/statefulset/"),
    ("DaemonSet",    "https://kubernetes.io/ko/docs/concepts/workloads/controllers/daemonset/"),
    ("Job",          "https://kubernetes.io/ko/docs/concepts/workloads/controllers/job/"),
    ("CronJob",      "https://kubernetes.io/ko/docs/concepts/workloads/controllers/cron-jobs/"),
    ("Service",      "https://kubernetes.io/ko/docs/concepts/services-networking/service/"),
    ("Ingress",      "https://kubernetes.io/ko/docs/concepts/services-networking/ingress/"),
    ("ConfigMap",    "https://kubernetes.io/ko/docs/concepts/configuration/configmap/"),
    ("Secret",       "https://kubernetes.io/ko/docs/concepts/configuration/secret/"),
    ("PersistentVolume", "https://kubernetes.io/ko/docs/concepts/storage/persistent-volumes/"),
    ("HPA",          "https://kubernetes.io/ko/docs/tasks/run-application/horizontal-pod-autoscale/"),
    ("OOM 리소스 할당", "https://kubernetes.io/ko/docs/tasks/configure-pod-container/assign-memory-resource/"),
    ("파드 라이프사이클", "https://kubernetes.io/ko/docs/concepts/workloads/pods/pod-lifecycle/"),
    ("헬스체크",     "https://kubernetes.io/ko/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/"),
    ("롤링 업데이트", "https://kubernetes.io/ko/docs/tutorials/kubernetes-basics/update/update-intro/"),
    ("RBAC",         "https://kubernetes.io/ko/docs/reference/access-authn-authz/rbac/"),
    ("NetworkPolicy", "https://kubernetes.io/ko/docs/concepts/services-networking/network-policies/"),
    ("리소스 쿼터",   "https://kubernetes.io/ko/docs/concepts/policy/resource-quotas/"),
    ("LimitRange",   "https://kubernetes.io/ko/docs/concepts/policy/limit-range/"),
    ("파드 디버깅",   "https://kubernetes.io/ko/docs/tasks/debug/debug-application/debug-pods/"),
    ("클러스터 장애", "https://kubernetes.io/ko/docs/tasks/debug/debug-cluster/troubleshooting/"),
    ("kubectl 치트시트", "https://kubernetes.io/ko/docs/reference/kubectl/cheatsheet/"),
    ("컴포넌트",     "https://kubernetes.io/ko/docs/concepts/overview/components/"),
    ("볼륨",         "https://kubernetes.io/ko/docs/concepts/storage/volumes/"),
    ("DNS",          "https://kubernetes.io/ko/docs/concepts/services-networking/dns-pod-service/"),
    ("보안 컨텍스트", "https://kubernetes.io/ko/docs/tasks/configure-pod-container/security-context/"),
    ("파드 QoS",     "https://kubernetes.io/ko/docs/concepts/workloads/pods/pod-qos/"),
    ("리소스 관리",   "https://kubernetes.io/ko/docs/concepts/configuration/manage-resources-containers/"),
]


def crawl_k8s_page(url: str) -> dict | None:
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # 페이지 제목 추출
        h1 = soup.find("h1")
        page_title = h1.get_text(strip=True) if h1 else url.split("/")[-2] or "문서"

        content_div = soup.find("div", {"class": "td-content"}) or soup.find("main")
        if not content_div:
            return None

        for tag in content_div.find_all(["script", "style", "nav", "footer", "aside"]):
            tag.decompose()

        text = content_div.get_text(separator="\n", strip=True)

        if len(text) < 200:
            return None

        full_title = f"쿠버네티스 - {page_title}"

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
            "language": "ko",
            "created_at": get_utc_now(),
            "published_date": None,
            "tags": ["쿠버네티스", "공식문서", "k8s"] + CATEGORY_TAGS,
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
    print("\n[k8s 크롤러] 시작...\n")
    results = []
    existing_urls = set()
    output_path = os.path.join(OUTPUT_DIR, "k8s_docs.json")

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

    # 사이트맵에서 URL 수집
    urls = get_urls_from_sitemap()

    # 사이트맵 실패 시 폴백
    if not urls:
        urls = [url for _, url in FALLBACK_URLS]

    new_urls = [url for url in urls if url not in existing_urls]
    print(f"\n전체 URL: {len(urls)}개 | 새로 크롤링: {len(new_urls)}개\n")

    if not new_urls:
        print("새로운 문서 없음 → 종료")
        return

    new_count = 0
    for url in new_urls:
        print(f"크롤링 중: {url}")
        doc = crawl_k8s_page(url)
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