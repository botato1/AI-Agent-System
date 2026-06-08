import sys
import httpx
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parents[3]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:7b"

def get_utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# ==================== 은어/약어 → 표준 용어 변환 ====================

def normalize_query(user_input: str) -> str:
    prompt = f"""당신은 개발 용어 변환 전문가입니다.
아래 개발자 입력에서 은어, 약어, 줄임말을 한국어 표준 개발 용어로 변환하세요.
반드시 한국어로 변환하고 변환된 문장만 출력하세요. 설명하지 마세요.

예시)
입력: OOM이 뭐야
변환: OOM이 뭐야

입력: JWT가 뭐야
변환: JWT가 뭐야

입력: 쿠버 파드 뻗었어
변환: 쿠버네티스(Kubernetes) Pod 장애 발생

입력: 디비 삑났어
변환: 데이터베이스(Database) 장애 발생

입력: 머지하다 충돌났어
변환: Git merge 충돌(conflict) 발생

입력: {user_input}
변환:"""

    response = httpx.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=30.0
    )
    result = response.json()
    return result.get("response", user_input).strip()


# ==================== 질문 의도 파악 ====================

def classify_intent(user_input: str) -> dict:
    prompt = f"""당신은 개발자 AI 비서입니다.
아래 질문의 의도를 분류하세요.
반드시 아래 4가지 중 하나만 출력하세요.

분류 기준:
- rag_search: 문서/회의록/지식 검색이 필요한 질문
- general: 일반적인 개발 질문 또는 용어 설명
- memory: 과거 대화나 이전 작업 내용을 묻는 질문
- task_extract: 할일/액션아이템 추출이 필요한 질문

예시)
질문: 저번 쿠버 OOM 터진거 어떻게 해결했지 → rag_search
질문: OOM이 뭐야 → general
질문: 아까 내가 뭐 물어봤지 → memory
질문: 오늘 회의에서 누가 뭐 해야해 → task_extract

질문: {user_input}
의도:"""

    response = httpx.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=30.0
    )
    result = response.json()
    intent = result.get("response", "general").strip().lower()

    valid_intents = ["rag_search", "general", "memory", "task_extract"]
    if intent not in valid_intents:
        intent = "general"

    return {"intent": intent, "original_input": user_input}

# ==================== 일반 답변 생성 ====================

def generate_answer(user_input: str, context: str = "") -> str:
    if context:
        prompt = f"""당신은 개발자 AI 비서입니다.
아래 참고 문서를 바탕으로 질문에 답하세요.
불필요한 인사말 없이 핵심만 답하세요.

참고 문서:
{context}

질문: {user_input}
답변:"""
    else:
        prompt = f"""당신은 개발자 AI 비서입니다.
질문에 핵심만 간결하게 답하세요.

질문: {user_input}
답변:"""

    response = httpx.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=60.0
    )
    result = response.json()
    return result.get("response", "답변 생성 실패").strip()

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