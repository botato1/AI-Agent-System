# scripts/test_load_meeting.py
#
# 합성 회의록 JSON을 document_loader.py로 직접 적재해서
# meeting_collection에 들어가는지, 검색이 되는지 확인하는 테스트 스크립트.
# 테스트 전용 — 프로그램 코드에 포함하지 말 것.
#
# 실행:
#   python -m scripts.test_load_meeting

import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from backend.modules.rag.chroma_client import (
    get_or_create_collection,
    MEETING_COLLECTION,
    insert_document,
    _load_bm25_index,
)
from backend.modules.rag.document_loader import _chunk_document, _get_upload_context, _build_base_meta

# ── 테스트 JSON 경로 ──────────────────────────────────────────
# data/meeting/ 폴더에 넣어서 사용
MEETING_JSON_FILES = [
    BASE_DIR / "data" / "uploads" / "test_meeting_001.json",
    BASE_DIR / "data" / "uploads" / "test_meeting_002.json",
    BASE_DIR / "data" / "uploads" / "test_meeting_003.json",
]

def load_test_meeting(json_path: Path, room_id: str = "test_room_001"):
    """테스트용 회의록 JSON을 직접 읽어서 ChromaDB에 적재한다."""

    print(f"[테스트 적재] {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    doc_type = doc.get("type", "meeting")
    doc_id = doc.get("id") or doc.get("document_id", "")
    upload_context = _get_upload_context(doc_type)
    base_meta = _build_base_meta(doc, room_id)

    # document_id 명시적으로 고정
    base_meta["document_id"] = doc_id

    chunks = doc.get("chunks", [])
    if not chunks:
        print("ERROR: chunks가 비어있음")
        return

    chunked = _chunk_document(chunks)
    print(f"청킹 결과: {len(chunked)}개 청크")

    for idx, chunk in enumerate(chunked):
        chunk_id = f"{doc_id}_chunk_{idx:04d}"
        metadata = {
            **base_meta,
            "chunk_index": idx,
            "page_number": chunk.get("page_number", 1),
            "upload_context": upload_context,
            "chroma_id": chunk_id,
            "document_id": doc_id,
        }
        insert_document({
            "id":      chunk_id,
            "content": chunk["content"],
            **metadata,
        })
        print(f"  [{idx}] 적재 완료: {repr(chunk['content'][:50])}")

    print(f"\n총 {len(chunked)}개 청크 적재 완료")

    # 적재 확인
    col = get_or_create_collection(MEETING_COLLECTION)
    print(f"meeting_collection 현재 총 문서 수: {col.count()}개")


def main():
    loaded = 0
    for json_path in MEETING_JSON_FILES:
        if not json_path.exists():
            print(f"[건너뜀] 파일 없음: {json_path}")
            continue
        load_test_meeting(json_path)
        loaded += 1
        print()

    print("="*60)
    print(f"총 {loaded}개 회의록 적재 완료.")
    print("이제 test_rag_answer.py를 실행해서 검색이 되는지 확인하세요.")
    print("="*60)


if __name__ == "__main__":
    main()