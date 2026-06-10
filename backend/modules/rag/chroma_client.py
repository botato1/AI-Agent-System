# backend/modules/rag/chroma_client.py
import os
import sys
import pickle
from pathlib import Path
from rank_bm25 import BM25Okapi

BASE_DIR = Path(__file__).resolve().parents[3]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

import chromadb
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction

CHROMA_DIR = os.path.join(BASE_DIR, "storage", "chroma")
BM25_DIR = os.path.join(BASE_DIR, "storage", "bm25")
os.makedirs(BM25_DIR, exist_ok=True)

chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)

# 컬렉션 이름 상수
MEETING_COLLECTION = "meeting_collection"
KNOWLEDGE_COLLECTION = "knowledge_collection"

# upload_context → 컬렉션 매핑
CONTEXT_TO_COLLECTION = {
    "voice": MEETING_COLLECTION,
    "meeting": MEETING_COLLECTION,
    "document": KNOWLEDGE_COLLECTION,
}


# ── 컬렉션 ────────────────────────────────────────────────────
def get_or_create_collection(collection_name: str):
    ollama_ef = OllamaEmbeddingFunction(
        url="http://localhost:11434/api/embeddings",
        model_name="bge-m3"
    )
    return chroma_client.get_or_create_collection(
        name=collection_name,
        embedding_function=ollama_ef,
        metadata={"hnsw:space": "cosine"}
    )


# ── BM25 인덱스 관리 ──────────────────────────────────────────
def _bm25_path(collection_name: str) -> str:
    return os.path.join(BM25_DIR, f"{collection_name}.pkl")

def _load_bm25_index(collection_name: str) -> dict:
    """저장된 BM25 인덱스 로드. 없으면 빈 구조 반환"""
    path = _bm25_path(collection_name)
    if os.path.exists(path):
        with open(path, "rb") as f:
            return pickle.load(f)
    return {"doc_ids": [], "tokenized_docs": []}

def _save_bm25_index(collection_name: str, index_data: dict):
    """BM25 인덱스 저장"""
    path = _bm25_path(collection_name)
    with open(path, "wb") as f:
        pickle.dump(index_data, f)

def _build_bm25(tokenized_docs: list) -> BM25Okapi:
    if not tokenized_docs:
        return BM25Okapi([[""]])
    return BM25Okapi(tokenized_docs)

def _update_bm25_index(collection_name: str, doc_id: str, document: str):
    """문서 추가 시 BM25 인덱스 업데이트"""
    index_data = _load_bm25_index(collection_name)
    index_data["doc_ids"].append(doc_id)
    index_data["tokenized_docs"].append(document.split())
    _save_bm25_index(collection_name, index_data)

def _remove_from_bm25_index(collection_name: str, doc_id: str):
    """문서 삭제 시 BM25 인덱스에서 제거"""
    index_data = _load_bm25_index(collection_name)
    if doc_id in index_data["doc_ids"]:
        idx = index_data["doc_ids"].index(doc_id)
        index_data["doc_ids"].pop(idx)
        index_data["tokenized_docs"].pop(idx)
        _save_bm25_index(collection_name, index_data)


# ── 문서 저장 ─────────────────────────────────────────────────
def insert_document(doc: dict):
    """upload_context 기준으로 컬렉션 자동 분류 후 저장"""
    upload_context = doc.get("upload_context", "document")
    collection_name = CONTEXT_TO_COLLECTION.get(upload_context, KNOWLEDGE_COLLECTION)
    collection = get_or_create_collection(collection_name)

    tags = doc.get("tags", [])
    if isinstance(tags, list):
        tags = ",".join(tags)

    collection.add(
        ids=[doc["id"]],
        documents=[doc["content"]],
        metadatas=[{
            "title": doc.get("title", ""),
            "type": doc.get("type", "document"),
            "source": doc.get("source", ""),
            "language": doc.get("language", "ko"),
            "created_at": doc.get("created_at", ""),
            "status": doc.get("status", "processed"),
            "notion_url": doc.get("notion_url") or "",
            "chroma_id": doc.get("id", ""),
            "error": doc.get("error") or "",
            "user_edited": doc.get("user_edited", False),
            "tags": tags,
            "importance_score": doc.get("importance_score", 50),
            "document_id": doc.get("document_id", ""),
            "filename": doc.get("filename", ""),
            "upload_context": upload_context,
            "chunk_index": doc.get("chunk_index", 0),
            "room_id": doc.get("room_id", ""),
        }]
    )

    # BM25 인덱스 업데이트
    _update_bm25_index(collection_name, doc["id"], doc["content"])
    print(f"[BGE-M3] 저장 완료 → {collection_name}: {doc.get('title', doc['id'])}")


# ── 하이브리드 검색 ───────────────────────────────────────────
def search_hybrid(
    query_text: str,
    top_k: int = 5,
    filter: dict = None,
    collection_name: str = None
):
    """
    BGE-M3 벡터 (70%) + BM25 키워드 (30%) 하이브리드 검색
    collection_name 없으면 두 컬렉션 모두 검색 후 합산
    """
    if collection_name:
        target_collections = [collection_name]
    else:
        target_collections = [MEETING_COLLECTION, KNOWLEDGE_COLLECTION]

    all_results = []

    for col_name in target_collections:
        collection = get_or_create_collection(col_name)

        # 벡터 검색
        try:
            dense_results = collection.query(
                query_texts=[query_text],
                n_results=top_k,
                where=filter
            )
        except Exception:
            continue

        if not dense_results or not dense_results["documents"]:
            continue

        # BM25 인덱스 로드
        index_data = _load_bm25_index(col_name)
        bm25 = _build_bm25(index_data["tokenized_docs"])
        bm25_scores = bm25.get_scores(query_text.split())
        bm25_score_map = {
            index_data["doc_ids"][i]: bm25_scores[i]
            for i in range(len(index_data["doc_ids"]))
        }

        # 점수 합산
        for i in range(len(dense_results["documents"][0])):
            doc_id = dense_results["ids"][0][i]
            document = dense_results["documents"][0][i]
            metadata = dense_results["metadatas"][0][i]
            distance = dense_results["distances"][0][i] if "distances" in dense_results else 1.0

            semantic_score = 1.0 - distance
            raw_bm25 = bm25_score_map.get(doc_id, 0.0)
            # BM25 점수 0~1로 정규화
            max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1.0
            keyword_score = min(raw_bm25 / max_bm25, 1.0)

            final_score = (semantic_score * 0.7) + (keyword_score * 0.3)

            all_results.append({
                "id": doc_id,
                "document": document,
                "metadata": metadata,
                "score": round(final_score, 4),
                "collection": col_name
            })

    all_results.sort(key=lambda x: x["score"], reverse=True)
    return all_results[:top_k]


# ── 문서 삭제 ─────────────────────────────────────────────────
def delete_document(doc_id: str, collection_name: str = None):
    """특정 컬렉션 또는 전체 컬렉션에서 문서 삭제"""
    targets = [collection_name] if collection_name else [MEETING_COLLECTION, KNOWLEDGE_COLLECTION]

    for col_name in targets:
        try:
            collection = get_or_create_collection(col_name)
            collection.delete(ids=[doc_id])
            _remove_from_bm25_index(col_name, doc_id)
            print(f"[삭제 완료] {col_name}: {doc_id}")
        except Exception:
            continue


if __name__ == "__main__":
    print("ChromaDB 연결 확인 중...")
    meeting_col = get_or_create_collection(MEETING_COLLECTION)
    knowledge_col = get_or_create_collection(KNOWLEDGE_COLLECTION)
    print(f"meeting_collection 준비 완료: {meeting_col.name}")
    print(f"knowledge_collection 준비 완료: {knowledge_col.name}")