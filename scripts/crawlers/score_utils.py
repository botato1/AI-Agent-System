# scripts/crawlers/score_utils.py
import re
import math
from datetime import datetime, timezone
from dateutil import parser as date_parser
from langdetect import detect, LangDetectException

# =========================
# tech_score 계산용 키워드
# =========================
TECH_SCORE_KEYWORDS = {
    # Level 5 (매우 고급/실무 핵심)
    "mcp": 5, "distributed system": 5, "분산시스템": 5,
    "consensus": 5, "raft": 5, "etcd": 5, "operator": 5,
    "controller": 5, "crd": 5, "cni": 5, "service mesh": 5,
    "sre": 5, "observability": 5,

    # Level 4 (고급 실무)
    "쿠버네티스": 4, "kubernetes": 4, "k8s": 4,
    "트러블슈팅": 4, "장애": 4, "장애대응": 4, "장애분석": 4,
    "스케일링": 4, "고가용성": 4, "failover": 4, "확장성": 4,
    "terraform": 4, "argocd": 4, "istio": 4, "prometheus": 4,
    "grafana": 4, "kafka": 4, "airflow": 4, "spark": 4,
    "cdc": 4, "lakehouse": 4, "elasticsearch": 4,
    "llm": 4, "rag": 4, "agent": 4, "embedding": 4,
    "vector db": 4, "vectordb": 4, "langgraph": 4, "fine tuning": 4,
    "마이그레이션": 4, "리팩토링": 4, "msa": 4, "마이크로서비스": 4,
    "아키텍처": 4,

    # Level 3 (중급 실무)
    "도커": 3, "docker": 3, "aws": 3, "gcp": 3, "azure": 3,
    "eks": 3, "ecs": 3, "lambda": 3, "redis": 3, "cache": 3,
    "캐시": 3, "database": 3, "데이터베이스": 3, "api": 3,
    "backend": 3, "보안": 3, "취약점": 3, "운영": 3,
    "모니터링": 3, "디버깅": 3, "파이프라인": 3, "helm": 3,
    "flux": 3, "pod": 3, "deployment": 3, "statefulset": 3,
    "daemonset": 3, "hpa": 3, "vpa": 3, "sdk": 3,
    "automation": 3, "자동화": 3,

    # Level 2 (일반 기술 주제)
    "react": 2, "nextjs": 2, "vue": 2, "typescript": 2,
    "javascript": 2, "python": 2, "java": 2, "golang": 2,
    "머신러닝": 2, "딥러닝": 2, "테스트": 2, "ci/cd": 2,
    "infra": 2, "인프라": 2,

    # Level 1 (너무 일반적이라 낮게)
    "개발": 1, "코드": 1, "시스템": 1, "서버": 1,
    "성능": 1, "최적화": 1, "오픈소스": 1, "알고리즘": 1,
}


# =========================
# 공식문서 출처별 가중치
# (기술 블로그는 0점 — authority_score 미적용)
# =========================
OFFICIAL_BONUS = {
    "kubernetes_docs": 10,
    "docker_docs": 9,
    "github_actions_docs": 7,
}


# =========================
# 카테고리 분류용 키워드 (tech_score와 별도 — 목적이 다름)
# =========================
CATEGORY_KEYWORDS = {
    "infra": [
        "쿠버네티스", "kubernetes", "k8s", "도커", "docker",
        "aws", "gcp", "azure", "장애", "장애대응", "sre",
        "terraform", "argocd", "istio", "prometheus", "grafana",
        "인프라", "infra", "배포", "모니터링", "observability",
        "helm", "pod", "deployment", "hpa", "스케일링", "고가용성",
    ],
    "frontend": [
        "react", "nextjs", "vue", "typescript", "javascript",
        "프론트엔드", "frontend", "웹뷰", "webview", "렌더링",
        "css", "ui", "ux", "컴포넌트",
    ],
    "backend": [
        "api", "spring", "fastapi", "database", "데이터베이스",
        "백엔드", "backend", "서버", "msa", "마이크로서비스",
        "아키텍처", "캐시", "cache", "redis",
    ],
}


# 키워드 1개당 카운트 상한 (반복 등장보다 키워드 다양성을 우선)
MAX_COUNT_PER_KEYWORD = 3


def calculate_keyword_score(text: str) -> tuple[int, list[str]]:
    """
    키워드 점수 합산 + 매칭된 키워드 목록.
    영문은 word boundary 적용, 한글은 포함 여부로 체크.

    같은 키워드가 여러 번 등장해도 영향이 과도하게 커지지 않도록
    saturation clamp(최대 3회) + log scale을 적용한다.
    → "단어 양"보다 "키워드 다양성"이 점수에 더 크게 반영됨.
    """
    score = 0.0
    keywords_found = []
    low_text = text.lower()

    for keyword, weight in TECH_SCORE_KEYWORDS.items():
        low_keyword = keyword.lower()

        if re.match(r'^[a-z0-9\s/]+$', low_keyword):
            pattern = rf"\b{re.escape(low_keyword)}\b"
            count = len(re.findall(pattern, low_text))
        else:
            count = low_text.count(low_keyword)

        if count > 0:
            capped_count = min(count, MAX_COUNT_PER_KEYWORD)
            # count=1 → log(1)=0 → factor=1 (기존과 동일)
            # count=3 → factor≈2.1 (상한 근접)
            score += weight * (1 + math.log(capped_count))
            keywords_found.append(keyword)

    return round(score), keywords_found


def calculate_freshness_score(date_str: str | None) -> int:
    """
    작성일 기준 최신성 점수.
    1년 이내 = 10, 1~2년 = 5, 2년 이상/파싱실패/날짜없음 = 0
    """
    if not date_str:
        return 0

    try:
        article_date = date_parser.parse(date_str, fuzzy=True)
        if article_date.tzinfo is None:
            article_date = article_date.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        days_diff = (now - article_date).days

        if days_diff <= 365:
            return 10
        elif days_diff <= 730:
            return 5
        else:
            return 0

    except Exception:
        return 0


def calculate_tech_score(
    title: str,
    content: str,
    date_str: str | None,
    source: str
) -> tuple[int, list[str]]:
    """
    tech_score = title_keyword_score * 3
                + body_keyword_score
                + authority_score (공식문서만 적용, OFFICIAL_BONUS 참조)
                + freshness_score

    body는 content[:3000] 기준으로 계산 (성능/정확도 균형)
    """
    title_score, title_keywords = calculate_keyword_score(title)
    body_score, body_keywords = calculate_keyword_score(content[:3000])

    authority_score = OFFICIAL_BONUS.get(source, 0)
    freshness_score = calculate_freshness_score(date_str)

    total_score = (title_score * 3) + body_score + authority_score + freshness_score
    keywords_found = list(set(title_keywords + body_keywords))

    return total_score, keywords_found


def is_within_years(date_str: str | None, years: int) -> bool:
    """
    date_str이 현재로부터 years년 이내인지 판단.
    날짜 파싱 실패 시 True (제외하지 않음 — 정보 유실 방지).
    """
    if not date_str:
        return True

    try:
        article_date = date_parser.parse(date_str, fuzzy=True)
        if article_date.tzinfo is None:
            article_date = article_date.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        days_diff = (now - article_date).days

        return days_diff <= (years * 365)

    except Exception:
        return True


def detect_category(title: str, content: str) -> tuple[str, list[str]]:
    """
    title + content[:3000] 기준으로 infra/frontend/backend 분류.
    presence 기반 (키워드 등장 횟수가 아니라 등장 여부로 점수 계산).
    동점이면 backend를 기본값으로.
    """
    text = (title + " " + content[:3000]).lower()

    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for k in keywords if k.lower() in text)
        scores[category] = score

    if max(scores.values()) == 0:
        best_category = "backend"
    else:
        best_category = max(scores, key=scores.get)

    tag_map = {
        "infra": ["인프라", "devops", "장애대응"],
        "frontend": ["프론트엔드", "성능최적화", "웹개발"],
        "backend": ["백엔드", "서버개발"],
    }

    return best_category, tag_map[best_category]

def detect_language(text: str) -> str:
    """
    content 앞부분을 기준으로 언어를 감지.
    한국어면 "ko", 그 외(영어 등)는 "en".
    감지 실패 시 "en".
    """
    if not text:
        return "en"

    try:
        sample = text[:1000]
        lang = detect(sample)
        return "ko" if lang == "ko" else "en"
    except LangDetectException:
        return "en"
