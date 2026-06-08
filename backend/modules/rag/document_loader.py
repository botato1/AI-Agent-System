import os
import sys
import uuid
import re
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parents[3]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from backend.modules.rag.chroma_client import insert_document

RAW_DATA_DIR = os.path.join(BASE_DIR, "data", "raw")

def get_utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# ==================== 파일 읽기 ====================

def load_txt(file_path: str) -> str:
    """TXT / MD 파일 읽기"""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def load_pdf(file_path: str) -> str:
    """PDF 파일 읽기 (PyMuPDF)"""
    try:
        import fitz
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except ImportError:
        print("PyMuPDF 없음 → pip install pymupdf")
        return ""

# ==================== 청크 분할 ====================

def smart_semantic_splitter(text: str, max_chunk_size: int = 800) -> list:
    """
    의미 단위 단락 분할
    줄바꿈 기준으로 문맥 유지하며 청킹
    """
    paragraphs = text.split("\n")
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current_chunk) + len(para) < max_chunk_size:
            current_chunk += para + "\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = para + "\n"

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

# ==================== 메타데이터 자동 태깅 ====================

def auto_tag_metadata(file_name: str, content: str) -> dict:
    """
    파일명/본문 특징으로 공통키 14개 자동 분류
    """
    now = get_utc_now()

    # 기본 메타데이터 (공통키 14개 기본값)
    metadata = {
        "title": file_name,
        "type": "document",        # 기본값
        "source": "text",          # 기본값
        "language": "ko",
        "created_at": now,
        "status": "processed",
        "notion_url": "",
        "chroma_id": "",
        "error": "",
        "user_edited": False,
        "tags": "일반",
        "importance_score": 50,    # 기본 중요도
    }

    # 회의록 감지
    if "meeting" in file_name.lower() or "회의록" in file_name:
        metadata["type"] = "meeting"
        metadata["importance_score"] = 85
        metadata["tags"] = "회의록"
        attendees = re.search(r"참석자:\s*([^\n]+)", content)
        if attendees:
            metadata["title"] = f"{file_name} ({attendees.group(1).strip()})"

    # 크롤링 데이터 감지
    elif "crawl" in file_name.lower() or "http" in content[:200]:
        metadata["type"] = "document"
        metadata["source"] = "text"
        metadata["importance_score"] = 60
        metadata["tags"] = "크롤링"

    # PDF 감지
    elif file_name.endswith(".pdf"):
        metadata["source"] = "pdf"
        metadata["type"] = "document"

    # MD 감지
    elif file_name.endswith(".md"):
        metadata["source"] = "md"

    return metadata

# ==================== 문서 적재 파이프라인 ====================

def load_and_insert(file_path: str):
    """
    파일 읽기 → 청크 분할 → 공통키 딕셔너리 생성 → ChromaDB 저장
    """
    file_name = os.path.basename(file_path)
    ext = os.path.splitext(file_name)[1].lower()

    # 파일 읽기
    if ext in [".txt", ".md"]:
        text = load_txt(file_path)
    elif ext == ".pdf":
        text = load_pdf(file_path)
    else:
        print(f"지원하지 않는 파일 형식: {ext}")
        return

    # 메타데이터 자동 태깅
    metadata = auto_tag_metadata(file_name, text)
    print(f"분류 결과 → type: {metadata['type']}, 중요도: {metadata['importance_score']}")

    # 청크 분할
    chunks = smart_semantic_splitter(text)
    print(f"총 {len(chunks)}개 청크로 분할됨")

    # 청크별 ChromaDB 저장
    for idx, chunk in enumerate(chunks):
        doc = {
            **metadata,
            "id": str(uuid.uuid4()),
            "content": chunk,
            "title": f"{metadata['title']} - chunk {idx + 1}",
            "chroma_id": "",      # insert 후 자동 채워짐
        }
        insert_document(doc)

    print(f"적재 완료: {file_name} ({len(chunks)}개 청크)")

def run_bulk_pipeline():
    """
    data/raw 폴더 전체 파일 자동 적재
    """
    print("\n[Embedder] 자동화 파이프라인 가동...\n")

    if not os.path.exists(RAW_DATA_DIR):
        os.makedirs(RAW_DATA_DIR)
        print(f"빈 데이터 폴더 생성됨: {RAW_DATA_DIR}")
        return

    file_list = [f for f in os.listdir(RAW_DATA_DIR)
                 if f.endswith((".txt", ".md", ".pdf"))]

    if not file_list:
        print("data/raw 폴더에 처리할 파일이 없습니다.")
        return

    for file_name in file_list:
        file_path = os.path.join(RAW_DATA_DIR, file_name)
        print(f"처리 시작: {file_name}")
        load_and_insert(file_path)

    print("\n[완료] 모든 파일 적재 완료")

if __name__ == "__main__":
    run_bulk_pipeline()