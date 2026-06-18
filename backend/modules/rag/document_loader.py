# backend/modules/rag/document_loader.py
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


def load_txt(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def load_pdf(file_path: str) -> str:
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


def smart_semantic_splitter(text: str, max_chunk_size: int = 800) -> list[str]:
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


def auto_tag_metadata(file_name: str, content: str) -> dict:
    now = get_utc_now()
    lower_file_name = file_name.lower()

    metadata = {
        "title": file_name,
        "type": "document",
        "source": "text",
        "language": "ko",
        "created_at": now,
        "status": "processed",
        "notion_url": "",
        "chroma_id": "",
        "error": "",
        "user_edited": False,
        "tags": "일반",
        "importance_score": 50,
    }

    if "meeting" in lower_file_name or "회의록" in file_name:
        metadata["type"] = "meeting"
        metadata["importance_score"] = 85
        metadata["tags"] = "회의록"

        attendees = re.search(r"참석자:\s*([^\n]+)", content)

        if attendees:
            metadata["title"] = f"{file_name} ({attendees.group(1).strip()})"

    elif "crawl" in lower_file_name or "http" in content[:200]:
        metadata["type"] = "document"
        metadata["source"] = "text"
        metadata["importance_score"] = 60
        metadata["tags"] = "크롤링"

    elif lower_file_name.endswith(".pdf"):
        metadata["source"] = "pdf"
        metadata["type"] = "document"

    elif lower_file_name.endswith(".md"):
        metadata["source"] = "md"

    return metadata


def load_and_insert(
    file_path: str,
    document_id: str | None = None,
    room_id: str | None = None,
    upload_context: str = "document"
) -> str | None:
    """
    문서를 읽어 청킹 후 ChromaDB에 저장한다.

    document_id, room_id는 document_service.py에서 생성한 값을 넘겨받아
    SQLite documents 테이블과 ChromaDB metadata를 동기화하기 위해 사용한다.
    """
    file_name = os.path.basename(file_path)
    ext = os.path.splitext(file_name)[1].lower()

    if ext in [".txt", ".md"]:
        text = load_txt(file_path)

    elif ext == ".pdf":
        text = load_pdf(file_path)

    else:
        print(f"지원하지 않는 파일 형식: {ext}")
        return None

    if not text.strip():
        print(f"문서에서 추출된 텍스트가 없습니다: {file_name}")
        return None

    # document_id가 없으면 기존 방식처럼 새로 생성
    # 단, 업로드 API에서는 document_service.py에서 만든 document_id를 넘겨주는 것이 원칙
    if not document_id:
        document_id = str(uuid.uuid4())

    metadata = auto_tag_metadata(file_name, text)
    print(f"분류 결과 → type: {metadata['type']}, 중요도: {metadata['importance_score']}")

    chunks = smart_semantic_splitter(text)
    print(f"총 {len(chunks)}개 청크로 분할됨")

    for idx, chunk in enumerate(chunks):
        doc = {
            **metadata,

            # chunk 자체의 고유 ID
            "id": str(uuid.uuid4()),

            # 실제 청크 내용
            "content": chunk,

            # 청크 제목
            "title": f"{metadata['title']} - chunk {idx + 1}",

            # SQLite documents.id와 동일한 문서 ID
            "document_id": document_id,

            # 파일명 검색용
            "filename": file_name,

            # 어느 채팅방에서 업로드된 문서인지
            "room_id": room_id or "",

            # 업로드 맥락
            "upload_context": upload_context,

            # 몇 번째 청크인지
            "chunk_index": idx,

            # 추후 Chroma 내부 id를 따로 저장할 경우 사용
            "chroma_id": "",
        }

        insert_document(doc)

    print(f"적재 완료: {file_name} ({len(chunks)}개 청크) | document_id: {document_id}")
    return document_id


def run_bulk_pipeline():
    print("\n[Embedder] 자동화 파이프라인 가동...\n")

    if not os.path.exists(RAW_DATA_DIR):
        os.makedirs(RAW_DATA_DIR)
        print(f"빈 데이터 폴더 생성됨: {RAW_DATA_DIR}")
        return

    file_list = [
        f for f in os.listdir(RAW_DATA_DIR)
        if f.endswith((".txt", ".md", ".pdf"))
    ]

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