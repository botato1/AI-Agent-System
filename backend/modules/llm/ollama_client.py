import os
import re
import sys
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

def get_utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def has_chinese(text: str) -> bool:
    return bool(re.search(r'[\u4e00-\u9fff]', text))

def normalize_query(user_input: str) -> str:
    prompt = f"""[INST] 당신은 한국어 개발 용어 변환기입니다.
반드시 한국어로만 출력하세요. 중국어 사용 절대 금지.
개발자 은어를 표준 용어로 변환하고 변환된 문장만 출력하세요.

예시)
입력: 쿠버 파드 뻗었어
변환: 쿠버네티스 Pod 장애 발생

입력: 디비 삑났어
변환: 데이터베이스 장애 발생

입력: OOM이 뭐야
변환: OOM이 뭐야

입력: JWT가 뭐야
변환: JWT가 뭐야

입력: {user_input}
변환: [/INST]"""

    response = httpx.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=30.0
    )
    result = response.json()
    response_text = result.get("response", user_input).strip()

    if has_chinese(response_text):
        print(f"[경고] 중국어 감지 → 원본 반환")
        return user_input

    return response_text

def classify_intent(user_input: str) -> dict:
    prompt = f"""[INST] 질문의 의도를 분류하세요.
반드시 아래 6가지 중 하나만 출력하세요. 다른 텍스트 출력 금지.

error_troubleshooting
past_record_search
document_summary
term_explanation
task_extraction
general

예시)
저번 쿠버 OOM 터진거 어떻게 해결했지 → past_record_search
OOM이 뭐야 → term_explanation
오늘 회의에서 누가 뭐 해야해 → task_extraction
CORS 에러 어떻게 고쳐 → error_troubleshooting
이 회의록 요약해줘 → document_summary
배포 어떻게 해 → general

질문: {user_input} [/INST]"""

    response = httpx.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=30.0
    )
    result = response.json()
    intent = result.get("response", "general").strip().lower()

    valid_intents = [
        "error_troubleshooting",
        "past_record_search",
        "document_summary",
        "term_explanation",
        "task_extraction",
        "general"
    ]
    if intent not in valid_intents:
        intent = "general"

    return {"intent": intent, "original_input": user_input}

def generate_answer(user_input: str, context: str = "") -> str:
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

if __name__ == "__main__":
    print("=== 은어 변환 테스트 ===")
    result = normalize_query("쿠버 파드 뻗었어")
    print(f"변환 결과: {result}")

    print("\n=== 의도 파악 테스트 ===")
    intent = classify_intent("저번 쿠버 OOM 터진거 어떻게 해결했지")
    print(f"의도: {intent}")

    print("\n=== 답변 생성 테스트 ===")
    answer = generate_answer("OOM이 뭐야")
    print(f"답변: {answer}")