# scripts/loaders/knowledge_loader.py
import json
import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))
from scripts.loaders.chunking_utils import chunk_document
from backend.modules.rag.chroma_client import (
    insert_document,
    get_or_create_collection,
    KNOWLEDGE_COLLECTION,
)

DATA_DIR = BASE_DIR / "data" / "knowledge"
TARGET_FILES = [
    DATA_DIR / "toss_blog.json",
    DATA_DIR / "woowahan_blog.json",
    DATA_DIR / "kakaopay_blog.json",
    DATA_DIR / "naver_blog.json",
    DATA_DIR / "k8s_docs.json",
    DATA_DIR / "docker_docs.json",
    DATA_DIR / "github_actions_docs.json",
]

def load_json(path: Path) -> list[dict]:
    if not path.exists():
        print(f"[knowledge_loader] 파일 없음: {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"[knowledge_loader] {path.name}: {len(data)}개 로드")
    return data

def already_exists(doc_id: str, collection) -> bool:
    """이미 적재된 문서인지 확인 (중복 적재 방지)"""
    try:
        result = collection.get(
            where={"document_id": doc_id},
            include=[],
        )
        return len(result.get("ids", [])) > 0
    except Exception:
        return False

def load_all():
    collection = get_or_create_collection(KNOWLEDGE_COLLECTION)
    total_docs   = 0
    total_chunks = 0
    skip_count   = 0

    for file_path in TARGET_FILES:
        documents = load_json(file_path)
        if not documents:
            continue

        print(f"\n{'='*50}")
        print(f"[knowledge_loader] {file_path.name} 적재 시작")
        print(f"{'='*50}")

        for doc in documents:
            doc_id = doc.get("id", "")
            title  = doc.get("title", "")

            if not doc_id or not doc.get("content", "").strip():
                print(f"[skip] id 또는 content 없음: {title}")
                skip_count += 1
                continue

            # 중복 적재 방지
            if already_exists(doc_id, collection):
                print(f"[skip] 이미 적재됨: {title[:40]}")
                skip_count += 1
                continue

            doc["upload_context"] = "knowledge"

            chunks = chunk_document(doc)
            if not chunks:
                print(f"[skip] 청킹 결과 없음: {title}")
                skip_count += 1
                continue

            chunk_count = 0
            for chunk in chunks:
                try:
                    insert_document({
                        **chunk,
                        "upload_context": "knowledge",
                        "status": "processed",
                        "notion_url": "",
                        "user_edited": False,
                        "importance_score": chunk.get("tech_score", 0),
                        "room_id": "",
                        "filename": "",
                    })
                    chunk_count += 1
                except Exception as e:
                    print(f"[error] 청크 적재 실패: {chunk.get('id')} → {e}")

            print(f"[완료] {title[:40]} → {chunk_count}개 청크 적재")
            total_docs   += 1
            total_chunks += chunk_count

    print(f"\n{'='*50}")
    print(f"[knowledge_loader] 적재 완료")
    print(f"  총 문서: {total_docs}개")
    print(f"  총 청크: {total_chunks}개")
    print(f"  건너뜀:  {skip_count}개")
    print(f"{'='*50}")

if __name__ == "__main__":
    load_all()