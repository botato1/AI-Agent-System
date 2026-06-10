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

# .env에서 Ollama 서버 주소랑 모델명 읽어옴. 없으면 로컬 기본값 사용.
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

def get_utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def has_chinese(text: str) -> bool:
    return bool(re.search(r'[\u4e00-\u9fff]', text))

# 은어/약어 -> 표준어 변환 
def normalize_query(user_input: str) -> str:
    # 파일 확장자 포함된 경우 변환 안함
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

    # JSON 형식으로 반환된 경우 파싱
    try:
        parsed = json.loads(response_text)
        response_text = parsed.get("normalized", response_text)
    except:
        pass

    if has_chinese(response_text):
        print(f"[경고] 중국어 감지 → 원본 반환")
        return user_input

    return response_text
# 사용자 질문 의도 파악
def classify_intent(user_input: str) -> dict:
    prompt = f"[INST] [의도파악] {user_input} [/INST]"

    response = httpx.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=30.0
    )
    result = response.json()
    response_text = result.get("response", "general").strip()

    # JSON 형식으로 반환된 경우 파싱
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
        "general"
    ]
    if intent not in valid_intents:
        intent = "general"

    return {"intent": intent, "original_input": user_input}
# 최종 답변 생성
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
# 화자분리 보완
def enhance_diarization(segments: list[dict]) -> list[dict]:
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

        # JSON 배열 부분만 추출
        json_match = response_text[response_text.find("["):response_text.rfind("]") + 1]
        enhanced = json.loads(json_match)

        if not enhanced:
            return segments

        print(f"[ollama_client] 화자분리 보완 완료: {len(enhanced)}개 발화")
        return enhanced

    except Exception as e:
        print(f"[ollama_client] 화자분리 보완 실패, 원본 사용: {e}")
        return segments

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
        {"speaker": "SPEAKER_00", "start": 12.1, "end": 15.0, "text": "네 좋습니다."},  # 잘못 분리된 케이스
    ]
    enhanced = enhance_diarization(test_segments)
    print(f"보완 결과: {enhanced}")

