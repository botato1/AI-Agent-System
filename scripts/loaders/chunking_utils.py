# scripts/loaders/chunking_utils.py
# 문단 기반 청킹 공통 로직
# knowledge_loader.py, document_loader.py 둘 다 import해서 사용

import os
import re
import sys
import httpx
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBEDDING_MODEL = "bge-m3"

# 청크 크기 설정
MIN_CHUNK_SIZE  = 500   # 권장 최소 청크 크기 (자)
MAX_CHUNK_SIZE  = 1700  # 권장 최대 청크 크기 (자)
MIN_PARA_SIZE   = 200   # 이 미만의 단독 청크는 인접 청크와 merge
OVERLAP_RATIO   = 0.15  # 청크 간 overlap 비율 (15%)
SIM_DROP_THRESH = 0.3   # 유사도 급락 기준 (이 이상 떨어지면 의미 변화로 판단)


# ── 임베딩 ────────────────────────────────────────────────────

def _embed(text: str) -> list[float]:
    """Ollama API로 단일 텍스트 임베딩 (BGE-M3)"""
    response = httpx.post(
        f"{OLLAMA_BASE_URL}/api/embeddings",
        json={"model": EMBEDDING_MODEL, "prompt": text},
        timeout=30.0,
    )
    return response.json().get("embedding", [])


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """코사인 유사도 계산"""
    if not a or not b:
        return 0.0
    dot   = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x ** 2 for x in a) ** 0.5
    norm_b = sum(x ** 2 for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ── 1단계: 문단 분리 ──────────────────────────────────────────

def split_into_paragraphs(content: str) -> list[str]:
    """
    텍스트를 문단 단위로 분리.
    빈 줄 기준으로 분리하고, 너무 짧은 줄은 앞 문단에 붙임.
    """
    if not content or not content.strip():
        return []

    # 빈 줄(\n\n) 기준으로 분리
    raw_paras = re.split(r"\n{2,}", content.strip())

    paragraphs = []
    for para in raw_paras:
        para = para.strip()
        if not para:
            continue

        # 50자 미만의 단편 문단은 앞 문단에 붙임
        if len(para) < 50 and paragraphs:
            paragraphs[-1] = paragraphs[-1] + " " + para
        else:
            paragraphs.append(para)

    return paragraphs


# ── 2단계: 유사도 기반 그룹화 ────────────────────────────────

def group_by_similarity(paragraphs: list[str]) -> list[list[str]]:
    """
    인접 문단 간 유사도를 계산해서 그룹화.
    유사도가 SIM_DROP_THRESH 이상 급락하면 새 그룹 시작.

    문단이 3개 미만이면 유사도 계산 생략 (전체를 하나의 그룹으로).
    """
    if not paragraphs:
        return []

    if len(paragraphs) < 3:
        return [paragraphs]

    print(f"[chunking] 문단 {len(paragraphs)}개 임베딩 중...")

    # 모든 문단 임베딩
    embeddings = []
    for i, para in enumerate(paragraphs):
        emb = _embed(para[:500])  # 500자 이상은 잘라서 임베딩 (속도)
        embeddings.append(emb)
        if (i + 1) % 10 == 0:
            print(f"[chunking] {i + 1}/{len(paragraphs)} 완료")

    # 인접 문단 간 유사도 계산
    similarities = []
    for i in range(len(embeddings) - 1):
        sim = _cosine_similarity(embeddings[i], embeddings[i + 1])
        similarities.append(sim)

    # 유사도 급락 지점에서 그룹 분리
    groups = []
    current_group = [paragraphs[0]]

    for i, sim in enumerate(similarities):
        prev_sim = similarities[i - 1] if i > 0 else sim
        drop = prev_sim - sim  # 유사도 감소량

        if drop >= SIM_DROP_THRESH:
            # 의미 변화 감지 → 새 그룹 시작
            groups.append(current_group)
            current_group = [paragraphs[i + 1]]
        else:
            current_group.append(paragraphs[i + 1])

    if current_group:
        groups.append(current_group)

    print(f"[chunking] {len(groups)}개 그룹으로 분리됨")
    return groups


# ── 3단계: 길이 보정 ──────────────────────────────────────────

def _split_by_sentences(text: str) -> list[str]:
    """문장 단위 분리 (. ! ? 기준)"""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sentences if s.strip()]


def adjust_chunk_length(groups: list[list[str]]) -> list[str]:
    """
    그룹별 길이 보정:
    - MAX_CHUNK_SIZE 초과: 문단 단위 또는 문장 단위로 분할
    - MIN_PARA_SIZE 미만 단독 청크: 인접 청크와 merge
    """
    chunks = []

    for group in groups:
        group_text = "\n\n".join(group)

        # 정상 범위 → 그대로
        if MIN_CHUNK_SIZE <= len(group_text) <= MAX_CHUNK_SIZE:
            chunks.append(group_text)
            continue

        # 초과: 문단 단위로 분할
        if len(group_text) > MAX_CHUNK_SIZE:
            if len(group) > 1:
                # 여러 문단 → 문단 단위 split 후 재그룹
                current = ""
                for para in group:
                    if len(current) + len(para) + 2 > MAX_CHUNK_SIZE and current:
                        chunks.append(current.strip())
                        current = para
                    else:
                        current = (current + "\n\n" + para).strip() if current else para
                if current:
                    chunks.append(current.strip())
            else:
                # 단일 문단 → 문장 단위 split
                sentences = _split_by_sentences(group_text)
                current = ""
                for sent in sentences:
                    if len(current) + len(sent) + 1 > MAX_CHUNK_SIZE and current:
                        chunks.append(current.strip())
                        current = sent
                    else:
                        current = (current + " " + sent).strip() if current else sent
                if current:
                    chunks.append(current.strip())
            continue

        # 부족: 일단 추가 (merge는 아래에서)
        chunks.append(group_text)

    # 200자 미만 극단적 소형 청크 → 인접 청크와 merge
    merged = []
    for chunk in chunks:
        if len(chunk) < MIN_PARA_SIZE and merged:
            merged[-1] = merged[-1] + "\n\n" + chunk
        else:
            merged.append(chunk)

    return merged


# ── 4단계: overlap 적용 ───────────────────────────────────────

def apply_overlap(chunks: list[str]) -> list[str]:
    """
    청크 간 15% overlap 적용.
    앞 청크의 끝 15%를 다음 청크 앞에 붙임.
    """
    if len(chunks) <= 1:
        return chunks

    overlapped = [chunks[0]]

    for i in range(1, len(chunks)):
        prev_chunk = chunks[i - 1]
        overlap_size = max(int(len(prev_chunk) * OVERLAP_RATIO), 50)
        overlap_text = prev_chunk[-overlap_size:].strip()
        overlapped.append(overlap_text + "\n\n" + chunks[i])

    return overlapped


# ── 메인 함수 ─────────────────────────────────────────────────

def chunk_document(doc: dict) -> list[dict]:
    """
    문서 하나를 청킹해서 청크 딕셔너리 리스트로 반환.

    입력 doc 필드:
    - id: 문서 ID
    - content: 본문
    - title, source, language, tech_score, keywords, category 등

    출력 청크 필드:
    - id: {doc_id}_chunk_{i}
    - content: 청크 텍스트
    - document_id: 원본 문서 ID
    - chunk_index: 청크 번호
    - start_para / end_para: 원본 문단 위치 (추정)
    - 나머지: 원본 문서 메타데이터 상속
    """
    content = doc.get("content", "").strip()
    doc_id  = doc.get("id", "")

    if not content:
        print(f"[chunking] {doc_id} content 없음 → 건너뜀")
        return []

    # 문서가 짧으면 청킹 없이 그대로 반환
    if len(content) <= MAX_CHUNK_SIZE:
        return [_make_chunk(doc, content, 0, 0, 0)]

    # 1. 문단 분리
    paragraphs = split_into_paragraphs(content)
    if not paragraphs:
        return [_make_chunk(doc, content, 0, 0, 0)]

    # 2. 유사도 기반 그룹화
    groups = group_by_similarity(paragraphs)

    # 3. 길이 보정
    chunks = adjust_chunk_length(groups)

    # 4. overlap 적용
    chunks = apply_overlap(chunks)

    # 5. 청크 딕셔너리 생성
    result = []
    para_cursor = 0
    for i, chunk_text in enumerate(chunks):
        # 청크가 몇 번째 문단에서 시작하는지 추정
        start_para = para_cursor
        chunk_para_count = max(1, chunk_text.count("\n\n") + 1)
        end_para   = start_para + chunk_para_count - 1
        para_cursor = end_para + 1

        result.append(_make_chunk(doc, chunk_text, i, start_para, end_para))

    print(f"[chunking] {doc_id} → {len(result)}개 청크")
    return result


def _make_chunk(
    doc: dict,
    chunk_text: str,
    chunk_index: int,
    start_para: int,
    end_para: int,
) -> dict:
    """청크 딕셔너리 생성 (메타데이터 상속)"""
    doc_id = doc.get("id", "")
    return {
        # 청크 식별자
        "id":           f"{doc_id}_chunk_{chunk_index}",
        "document_id":  doc_id,
        "chunk_index":  chunk_index,
        "start_para":   start_para,
        "end_para":     end_para,

        # 청크 본문
        "content": chunk_text,

        # 원본 문서 메타데이터 상속
        "title":        doc.get("title", ""),
        "type":         doc.get("type", "document"),
        "source":       doc.get("source", ""),
        "category":     doc.get("category", ""),
        "language":     doc.get("language", "ko"),
        "created_at":   doc.get("created_at", ""),
        "published_date": doc.get("published_date", ""),
        "tags":         doc.get("tags", []),
        "keywords":     doc.get("keywords", []),
        "tech_score":   doc.get("tech_score", 0),
        "url":          doc.get("url", ""),
        "upload_context": doc.get("upload_context", "document"),
    }