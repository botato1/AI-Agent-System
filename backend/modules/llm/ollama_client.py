# backend/modules/llm/ollama_client.py
import os
import re
import sys
import json
import httpx
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[3]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

load_dotenv(BASE_DIR / ".env")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")


# ── 유틸 ─────────────────────────────────────────────────────
def get_utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def has_chinese(text: str) -> bool:
    return bool(re.search(r'[\u4e00-\u9fff]', text))


# ── 시스템 프롬프트 ───────────────────────────────────────────
DOBY_SYSTEM_GUIDE = """
너는 도비(Doby)라는 IT 프로젝트 업무 지원 AI 비서야.

[주요 역할]
- 업로드된 문서, PDF, 회의록, 개발 자료를 요약하고 설명한다.
- 문서 기반 질문에 답변한다.
- 회의록에서 담당자, 할 일, 마감일을 정리한다.
- 개인 일정이나 업무 일정을 정리하고 관리할 수 있도록 돕는다.
- 이전 답변이나 분석 결과를 Notion 저장 흐름과 연결한다.
- 개발자, IT 직무 종사자, 프로젝트 팀원이 업무를 정리할 수 있도록 돕는다.

[제한 사항]
- 날씨, 뉴스, 주식, 실시간 검색처럼 현재 시스템에서 지원하지 않는 기능을 할 수 있다고 말하지 않는다.
- 지원하지 않는 기능을 물으면 불가능하다고만 끝내지 말고, 이 서비스에서 가능한 IT 문서/회의록/일정/업무 정리 기능을 안내한다.
- 참고 문서가 필요한 질문인데 참고 문서가 없으면 추측하지 않는다.
- 답변은 한국어로 작성한다.
"""


# ── 기본 LLM 호출 함수들 ──────────────────────────────────────
def normalize_query(user_input: str) -> str:
    """은어/약어 → 표준어 변환"""
    if re.search(r'\.(pdf|docx|doc|md|txt|xlsx|pptx|csv)', user_input, re.IGNORECASE):
        return user_input

    prompt = f"[INST] [은어변환] {user_input} [/INST]"

    response = httpx.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=30.0
    )
    result = response.json()
    response_text = result.get("response", user_input).strip()

    try:
        parsed = json.loads(response_text)
        response_text = parsed.get("normalized", response_text)
    except:
        pass

    if has_chinese(response_text):
        print(f"[경고] 중국어 감지 → 원본 반환")
        return user_input

    return response_text


def classify_intent(user_input: str) -> dict:
    """사용자 질문 의도 파악"""
    prompt = f"[INST] [의도파악] {user_input} [/INST]"

    response = httpx.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=30.0
    )
    result = response.json()
    response_text = result.get("response", "general").strip()

    try:
        parsed = json.loads(response_text)
        intent = parsed.get("intent", "general").strip().lower()
    except:
        intent = response_text.strip().lower()

    valid_intents = [
        "error_troubleshooting",
        "past_record_search",
        "document_summary",
        "term_explanation",
        "task_extraction",
        "notion_save",
        "memory_search",
        "document_question",
        "general"
    ]
    if intent not in valid_intents:
        intent = "general"

    return {"intent": intent, "original_input": user_input}


def generate_answer(user_input: str, context: str = "") -> str:
    """기본 LLM 호출 — 프롬프트 직접 넘길 때 사용"""
    if context:
        prompt = f"""[INST] 당신은 한국어 개발자 AI 비서입니다.
반드시 한국어로만 답하세요. 중국어 사용 절대 금지.
아래 참고 문서를 바탕으로 질문에 답하세요.
인사말 없이 핵심만 답하세요.

참고 문서:
{context}

질문: {user_input} [/INST]"""
    else:
        prompt = f"""[INST] 당신은 한국어 개발자 AI 비서입니다.
반드시 한국어로만 답하세요. 중국어 사용 절대 금지.
질문에 핵심만 간결하게 답하세요.

질문: {user_input} [/INST]"""

    response = httpx.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=60.0
    )
    result = response.json()
    response_text = result.get("response", "답변 생성 실패").strip()

    if has_chinese(response_text):
        print(f"[경고] 중국어 감지 → 재시도")
        response = httpx.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt + "\n한국어로만 답하세요.", "stream": False},
            timeout=60.0
        )
        result = response.json()
        response_text = result.get("response", "답변 생성 실패").strip()

    return response_text


# ── 흐름별 답변 생성 ──────────────────────────────────────────
def generate_answer_for_graph(
    user_message: str,
    question_type: str = "general",
    rag_context: str = "",
    memory_context: str = "",
    tasks: list = None,
) -> str:
    """
    question_type에 따라 프롬프트 자동 구성 후 LLM 호출.
    ollama_service.py에서 question_type만 넘겨주면 됨.
    """
    tasks = tasks or []
    rag_context = rag_context or ""
    memory_context = memory_context or ""

    if question_type == "document_summary":
        prompt = f"""
{DOBY_SYSTEM_GUIDE}

아래 참고 문서 내용만 사용해서 사용자가 요청한 문서를 요약해줘.

[규칙]
- 참고 문서에 없는 내용은 추측하지 마라.
- 핵심 내용, 주요 근거, 결론 순서로 정리해라.
- 맞춤법과 띄어쓰기를 자연스럽게 다듬어라.
- 기술 용어는 일반적으로 쓰이는 표현을 사용해라.
- 답변은 한국어로 작성해라.

사용자 질문:
{user_message}
"""
        return generate_answer(prompt, context=rag_context)

    if question_type in ("document_question", "error_troubleshooting") and rag_context:
        prompt = f"""
{DOBY_SYSTEM_GUIDE}

아래 참고 문서 내용만 사용해서 사용자 질문에 답해줘.

[규칙]
- 참고 문서에 있는 내용만 근거로 답해라.
- 참고 문서에 없는 내용은 모른다고 답해라.
- 답변은 한국어로 작성해라.

사용자 질문:
{user_message}
"""
        return generate_answer(prompt, context=rag_context)

    if question_type == "task_extract" and tasks:
        task_context = json.dumps(tasks, ensure_ascii=False, indent=2)
        prompt = f"""
{DOBY_SYSTEM_GUIDE}

아래 추출된 할 일 목록을 보기 좋게 정리해줘.

[규칙]
- 담당자, 할 일, 마감일이 있으면 구분해서 정리해라.
- 없는 정보는 임의로 만들지 마라.
- 마감일 형식은 가능한 한 통일해서 보여줘라.
- 답변은 한국어로 작성해라.

사용자 질문:
{user_message}

할 일 목록:
{task_context}
"""
        return generate_answer(prompt, context=task_context)

    if question_type == "memory_search" and memory_context:
        prompt = f"""
{DOBY_SYSTEM_GUIDE}

아래 이전 대화 기록을 참고해서 사용자 요청에 답해줘.

[규칙]
- 이전 대화 기록에 있는 내용만 근거로 답해라.
- 이전 대화 기록에 없는 내용은 임의로 만들지 마라.
- 답변은 한국어로 작성해라.

사용자 질문:
{user_message}
"""
        return generate_answer(prompt, context=memory_context)

    # general 또는 fallback
    prompt = f"""
{DOBY_SYSTEM_GUIDE}

사용자 질문에 답해줘.

[규칙]
- 도비가 할 수 있는 일은 IT 프로젝트 업무 지원, 문서 요약, 회의록 정리, 문서 기반 질의응답, 할 일 추출, Notion 저장 보조이다.
- 날씨, 뉴스, 주식, 실시간 검색 같은 기능을 할 수 있다고 말하지 마라.
- 답변은 한국어로 작성해라.

사용자 질문:
{user_message}
"""
    return generate_answer(prompt)


# ── 할 일 추출 ────────────────────────────────────────────────
def extract_tasks_from_content(content: str) -> list[dict]:
    """회의록/문서에서 담당자별 할 일 추출"""
    if not content or not content.strip():
        return []

    prompt = f"""
아래 회의록 또는 문서에서 담당자별 할 일을 JSON 배열로만 추출해줘.

[규칙]
- 반드시 JSON 배열만 반환해라.
- 각 항목은 task_id, task, assignee, deadline, status 필드를 가져야 한다.
- task_id는 "0001", "0002" 형식으로 생성해라.
- 담당자나 마감일이 없으면 null로 둔다.
- status 기본값은 "todo"로 둔다.
- 원문에 없는 내용은 만들지 마라.
- 설명 문장은 쓰지 마라.

[마감일 규칙]
- 원문에 연도가 있으면 "YYYY년 M월 D일" 형식으로 작성해라.
- 원문에 연도가 없고 월/일만 있으면 원문 표현 그대로 사용해라.
- 마감일을 알 수 없으면 null로 둔다.

원본 내용:
{content}

JSON:
"""

    raw_answer = generate_answer(prompt, context=content)
    return _parse_json_array(raw_answer)


# ── Notion 저장용 요약 ────────────────────────────────────────
def generate_summary_for_notion(content: str) -> str | None:
    """Notion 저장용 요약 생성"""
    if not content or not content.strip():
        return None

    prompt = f"""
아래 원본 내용을 Notion에 함께 저장할 요약문으로 정리해줘.

[규칙]
- 원본에 없는 내용은 추가하지 마라.
- 핵심 내용만 간결하게 정리해라.
- 한국어로 작성해라.
- 제목은 만들지 마라.
- 3~5개 bullet point 또는 짧은 문단으로 작성해라.

원본 내용:
{content}

요약:
"""
    return generate_answer(prompt, context=content)


# ── 화자분리 보완 ─────────────────────────────────────────────
def enhance_diarization(segments: list[dict]) -> list[dict]:
    """
    STT 화자분리 결과 보완.
    문맥 기반으로 잘못 분리된 발화 수정, speaker 레이블은 유지.
    중국어 감지 or JSON 파싱 실패 시 원본 segments 그대로 반환.
    """
    transcript = "\n".join(
        f"[{s.get('speaker', 'UNKNOWN')} {s.get('start', 0):.1f}s] {s.get('text', '')}"
        for s in segments
    )

    prompt = f"""[INST] [화자분리보완]
아래는 자동 화자분리된 STT 결과입니다.
문맥을 보고 잘못 분리된 발화만 수정하세요.
speaker 레이블(SPEAKER_00 등)은 변경하지 말고 그대로 유지하세요.
반드시 아래 JSON 배열 형식으로만 출력하세요. 다른 말 하지 마세요.
중국어 사용 절대 금지.

입력:
{transcript}

출력 형식:
[
  {{"speaker": "SPEAKER_00", "start": 0.0, "end": 3.2, "text": "발화 내용"}},
  ...
] [/INST]"""

    try:
        response = httpx.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=60.0
        )
        response_text = response.json().get("response", "").strip()

        if has_chinese(response_text):
            print(f"[경고] 화자분리 중국어 감지 → 원본 반환")
            return segments

        json_match = response_text[response_text.find("["):response_text.rfind("]") + 1]
        enhanced = json.loads(json_match)

        if not enhanced:
            return segments

        print(f"[ollama_client] 화자분리 보완 완료: {len(enhanced)}개 발화")
        return enhanced

    except Exception as e:
        print(f"[ollama_client] 화자분리 보완 실패, 원본 사용: {e}")
        return segments


# ── 내부 유틸 ─────────────────────────────────────────────────
def _parse_json_array(text: str) -> list[dict]:
    """LLM 응답에서 JSON 배열만 추출"""
    if not text:
        return []

    cleaned = re.sub(r"```json", "", text.strip())
    cleaned = re.sub(r"```", "", cleaned).strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "tasks" in parsed:
            return parsed["tasks"]
        return []
    except:
        match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if not match:
            return []
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, list) else []
        except:
            return []


# ── 테스트 ────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== 은어 변환 테스트 ===")
    result = normalize_query("쿠버 파드 뻗었어")
    print(f"변환 결과: {result}")

    print("\n=== 파일명 보존 테스트 ===")
    result2 = normalize_query("무도_하지마_7장_보고서.pdf 요약해줘")
    print(f"변환 결과: {result2}")

    print("\n=== 의도 파악 테스트 ===")
    intent = classify_intent("저번 쿠버 OOM 터진거 어떻게 해결했지")
    print(f"의도: {intent}")

    print("\n=== 화자분리 보완 테스트 ===")
    test_segments = [
        {"speaker": "SPEAKER_00", "start": 0.0,  "end": 3.2,  "text": "오늘 회의 시작할게요."},
        {"speaker": "SPEAKER_01", "start": 3.5,  "end": 7.1,  "text": "네 준비됐습니다."},
        {"speaker": "SPEAKER_00", "start": 7.3,  "end": 12.0, "text": "먼저 지난주 이슈 정리부터 하겠습니다."},
        {"speaker": "SPEAKER_00", "start": 12.1, "end": 15.0, "text": "네 좋습니다."},
    ]
    enhanced = enhance_diarization(test_segments)
    print(f"보완 결과: {enhanced}")