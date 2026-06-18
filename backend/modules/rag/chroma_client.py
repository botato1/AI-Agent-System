# backend/modules/rag/chroma_client.py
import os
import sys
import pickle
from pathlib import Path
from rank_bm25 import BM25Okapi
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

BASE_DIR = Path(__file__).resolve().parents[3]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

import chromadb
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction

CHROMA_DIR = os.path.join(BASE_DIR, "storage", "chroma")
BM25_DIR = os.path.join(BASE_DIR, "storage", "bm25")
os.makedirs(BM25_DIR, exist_ok=True)

chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)

# ── 컬렉션 이름 상수 ──────────────────────────────────────────
MEETING_COLLECTION  = "meeting_collection"
DOCUMENT_COLLECTION = "document_collection"
KNOWLEDGE_COLLECTION = "knowledge_collection"

CONTEXT_TO_COLLECTION = {
    "voice":    MEETING_COLLECTION,
    "meeting":  MEETING_COLLECTION,
    "document": DOCUMENT_COLLECTION,
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
    path = _bm25_path(collection_name)
    if os.path.exists(path):
        with open(path, "rb") as f:
            return pickle.load(f)
    return {"doc_ids": [], "tokenized_docs": []}


def _save_bm25_index(collection_name: str, index_data: dict):
    path = _bm25_path(collection_name)
    with open(path, "wb") as f:
        pickle.dump(index_data, f)


def _build_bm25(tokenized_docs: list) -> BM25Okapi:
    if not tokenized_docs:
        return BM25Okapi([[""]])
    return BM25Okapi(tokenized_docs)


def _update_bm25_index(collection_name: str, doc_id: str, document: str):
    index_data = _load_bm25_index(collection_name)
    index_data["doc_ids"].append(doc_id)
    index_data["tokenized_docs"].append(document.split())
    _save_bm25_index(collection_name, index_data)


def _remove_from_bm25_index(collection_name: str, doc_id: str):
    index_data = _load_bm25_index(collection_name)
    if doc_id in index_data["doc_ids"]:
        idx = index_data["doc_ids"].index(doc_id)
        index_data["doc_ids"].pop(idx)
        index_data["tokenized_docs"].pop(idx)
        _save_bm25_index(collection_name, index_data)


# ── 문서 저장 ─────────────────────────────────────────────────
def insert_document(doc: dict):
    upload_context = doc.get("upload_context", "document")
    collection_name = CONTEXT_TO_COLLECTION.get(upload_context, KNOWLEDGE_COLLECTION)
    collection = get_or_create_collection(collection_name)

    tags = doc.get("tags", [])
    if isinstance(tags, list):
        tags = ",".join(tags)

    metadata = {
        "title":            doc.get("title", ""),
        "type":             doc.get("type", "document"),
        "source":           doc.get("source", ""),
        "language":         doc.get("language", "ko"),
        "created_at":       doc.get("created_at", ""),
        "status":           doc.get("status", "processed"),
        "notion_url":       doc.get("notion_url") or "",
        "chroma_id":        doc.get("id", ""),
        "error":            doc.get("error") or "",
        "user_edited":      doc.get("user_edited", False),
        "tags":             tags,
        "importance_score": doc.get("importance_score", 50),
        "document_id":      doc.get("document_id", ""),
        "filename":         doc.get("filename", ""),
        "upload_context":   upload_context,
        "chunk_index":      doc.get("chunk_index", 0),
        "room_id":          doc.get("room_id", ""),
        "tech_score":       doc.get("tech_score", 0),
    }

    collection.add(
        ids=[doc["id"]],
        documents=[doc["content"]],
        metadatas=[metadata]
    )
    _update_bm25_index(collection_name, doc["id"], doc["content"])
    print(f"[BGE-M3] 저장 완료 → {collection_name}: {doc.get('title', doc['id'])}")


# ── Reranker ─────────────────────────────────────────────────
_reranker = None

def _get_reranker():
    global _reranker
    if _reranker is None:
        from FlagEmbedding import FlagReranker
        # use_fp16=False + devices=["cpu"]로 안전하게 로드.
        # GPU+fp16 조합에서 환경에 따라 프로세스가 에러 없이
        # 죽는 문제가 있어 CPU/fp32로 고정해서 안정성 우선.
        # (속도가 더 필요해지면 devices=["cuda:0"]로 다시 전환 가능,
        #  단 그 경우 use_fp16=False부터 먼저 테스트할 것)
        print("[reranker] BAAI/bge-reranker-v2-m3 로딩 중 (CPU, fp32)...")
        _reranker = FlagReranker(
            "BAAI/bge-reranker-v2-m3",
            use_fp16=False,
            devices=["cpu"],
        )
        print("[reranker] 로딩 완료")
    return _reranker


def rerank_results(query_text: str, results: list[dict]) -> list[dict]:
    """
    results 각각의 content와 query를 cross-encoder로 재평가.
    각 결과에 reranker_score 필드를 추가하고 반환 (정렬은 하지 않음).
    FlagEmbedding 미설치/로딩실패 시 reranker_score = hybrid_score로 fallback.
    """
    if not results:
        return results

    try:
        reranker = _get_reranker()
        pairs = [[query_text, r.get("content", "")] for r in results]
        scores = reranker.compute_score(pairs, normalize=True)

        if isinstance(scores, float):
            scores = [scores]

        for r, s in zip(results, scores):
            r["reranker_score"] = float(s)

    except Exception as e:
        print(f"[rerank_results] reranker 실패, hybrid_score로 fallback: {e}")
        for r in results:
            r["reranker_score"] = r.get("score", 0.0)

    return results


# ── 하이브리드 검색 ───────────────────────────────────────────
def search_hybrid(
    query_text: str,
    top_k: int = 60,
    filter: dict | None = None,
    collection_name: str | None = None
):
    target_collections = [collection_name] if collection_name else [
        MEETING_COLLECTION, DOCUMENT_COLLECTION, KNOWLEDGE_COLLECTION
    ]

    all_results = []

    print("[search_hybrid] query_text:", query_text)
    print("[search_hybrid] filter:", filter)
    print("[search_hybrid] target_collections:", target_collections)

    for col_name in target_collections:
        collection = get_or_create_collection(col_name)

        try:
            query_kwargs = {
                "query_texts": [query_text],
                "n_results": top_k,
                "include": ["documents", "metadatas", "distances"],
            }
            if filter:
                query_kwargs["where"] = filter

            dense_results = collection.query(**query_kwargs)

        except Exception as e:
            print(f"[search_hybrid 에러] collection: {col_name}, error: {e}")
            continue

        if not dense_results:
            continue

        documents = dense_results.get("documents", [[]])
        ids       = dense_results.get("ids", [[]])
        metadatas = dense_results.get("metadatas", [[]])
        distances = dense_results.get("distances", [[]])

        if not documents or not documents[0]:
            continue

        print(f"[search_hybrid] collection: {col_name}, dense count: {len(documents[0])}")

        index_data = _load_bm25_index(col_name)
        bm25       = _build_bm25(index_data["tokenized_docs"])
        bm25_scores = bm25.get_scores(query_text.split())

        bm25_score_map = {
            index_data["doc_ids"][i]: bm25_scores[i]
            for i in range(len(index_data["doc_ids"]))
        }
        max_bm25 = max(bm25_scores) if len(bm25_scores) > 0 and max(bm25_scores) > 0 else 1.0

        for i in range(len(documents[0])):
            doc_id   = ids[0][i]
            document = documents[0][i]
            metadata = metadatas[0][i]
            distance = distances[0][i] if distances and distances[0] else 1.0

            semantic_score = 1.0 - distance
            raw_bm25       = bm25_score_map.get(doc_id, 0.0)
            keyword_score  = min(raw_bm25 / max_bm25, 1.0)
            final_score    = (semantic_score * 0.7) + (keyword_score * 0.3)

            all_results.append({
                "id":          doc_id,
                "content":     document,
                "document":    document,
                "metadata":    metadata,
                "score":       round(final_score, 4),
                "collection":  col_name,
                "title":       metadata.get("title", ""),
                "source":      metadata.get("source", ""),
                "filename":    metadata.get("filename", ""),
                "document_id": metadata.get("document_id", ""),
                "room_id":     metadata.get("room_id", ""),
                "chunk_index": metadata.get("chunk_index", 0),
            })

    all_results.sort(key=lambda x: x["score"], reverse=True)
    print("[search_hybrid] final count:", len(all_results[:top_k]))
    return all_results[:top_k]


# ── ChromaDB 직접 확인용 ──────────────────────────────────────
def get_documents_by_document_id(document_id: str) -> dict:
    total_ids, total_metadatas, total_documents = [], [], []

    for collection_name in [MEETING_COLLECTION, DOCUMENT_COLLECTION, KNOWLEDGE_COLLECTION]:
        collection = get_or_create_collection(collection_name)
        try:
            result = collection.get(
                where={"document_id": document_id},
                include=["metadatas", "documents"]
            )
            total_ids.extend(result.get("ids", []))
            total_metadatas.extend(result.get("metadatas", []))
            total_documents.extend(result.get("documents", []))
        except Exception as e:
            print(f"[Chroma get 에러] collection: {collection_name}, error: {e}")

    return {
        "ids":       total_ids,
        "metadatas": total_metadatas,
        "documents": total_documents,
        "count":     len(total_ids),
    }


# ── 문서 삭제 ─────────────────────────────────────────────────
def delete_document(doc_id: str, collection_name: str | None = None):
    targets = [collection_name] if collection_name else [
        MEETING_COLLECTION, DOCUMENT_COLLECTION, KNOWLEDGE_COLLECTION
    ]
    for col_name in targets:
        try:
            collection = get_or_create_collection(col_name)
            collection.delete(ids=[doc_id])
            _remove_from_bm25_index(col_name, doc_id)
            print(f"[삭제 완료] {col_name}: {doc_id}")
        except Exception as e:
            print(f"[삭제 에러] {col_name}: {doc_id}, error: {e}")


if __name__ == "__main__":
    print("ChromaDB 연결 확인 중...")
    for name in [MEETING_COLLECTION, DOCUMENT_COLLECTION, KNOWLEDGE_COLLECTION]:
        col = get_or_create_collection(name)
        print(f"{name} 준비 완료: {col.name}")