import os
import chromadb
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]
CHROMA_DIR = os.path.join(BASE_DIR, "storage", "chroma")

chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
COLLECTION_NAME = "knowledge_base"

def get_or_create_collection():
    """BGE-M3 임베딩 모델 연동 컬렉션 반환"""
    ollama_ef = OllamaEmbeddingFunction(
        url="http://localhost:11434/api/embeddings",
        model_name="bge-m3"
    )
    return chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ollama_ef,
        metadata={"hnsw:space": "cosine"}
    )

def insert_document(doc: dict):
    """
    공통키 14개 규격에 맞춰 ChromaDB에 문서 저장
    doc = 공통키 14개 + importance_score 담긴 딕셔너리
    """
    collection = get_or_create_collection()

    # tags가 list면 콤마 문자열로 변환 (Chroma는 list 지원 안함)
    tags = doc.get("tags", [])
    if isinstance(tags, list):
        tags = ",".join(tags)

    collection.add(
        ids=[doc["id"]],
        documents=[doc["content"]],
        metadatas=[{
            # 공통키 14개
            "title": doc.get("title", ""),
            "type": doc.get("type", "document"),
            "source": doc.get("source", ""),
            "language": doc.get("language", "ko"),
            "created_at": doc.get("created_at", ""),
            "status": doc.get("status", "processed"),
            "notion_url": doc.get("notion_url", ""),
            "chroma_id": doc.get("id", ""),
            "error": doc.get("error", ""),
            "user_edited": doc.get("user_edited", False),
            "tags": tags,
            # 승주 전용 키
            "importance_score": doc.get("importance_score", 50),
        }]
    )
    print(f"[BGE-M3] 문서 저장 완료: {doc.get('title', doc['id'])}")

def search_hybrid(query_text: str, top_k: int = 5, filter: dict = None):
    """
    하이브리드 검색
    - Semantic Search (BGE-M3 벡터 유사도)
    - Keyword Scoring (BM25 개념 이식)
    - 최종 점수 = 의미론 70% + 키워드 30%
    """
    collection = get_or_create_collection()

    # 1. 의미론적 검색
    dense_results = collection.query(
        query_texts=[query_text],
        n_results=top_k,
        where=filter
    )

    formatted_results = []
    if dense_results and dense_results["documents"]:
        for i in range(len(dense_results["documents"][0])):
            doc_id = dense_results["ids"][0][i]
            document = dense_results["documents"][0][i]
            metadata = dense_results["metadatas"][0][i]
            distance = dense_results["distances"][0][i] if "distances" in dense_results else 1.0
            semantic_score = 1.0 - distance

            # 2. 키워드 매칭 가산점 (BM25 개념)
            keyword_score = 0.0
            for word in query_text.split():
                if word in document:
                    keyword_score += 0.25

            # 3. 최종 하이브리드 점수 (의미론 70% + 키워드 30%)
            final_score = (semantic_score * 0.7) + (keyword_score * 0.3)

            formatted_results.append({
                "id": doc_id,
                "document": document,
                "metadata": metadata,
                "score": round(final_score, 4)
            })

    # 점수 높은 순 정렬
    formatted_results.sort(key=lambda x: x["score"], reverse=True)
    return formatted_results[:top_k]

def delete_document(doc_id: str):
    """문서 ID로 삭제 (수정 시 삭제 후 재삽입)"""
    collection = get_or_create_collection()
    collection.delete(ids=[doc_id])
    print(f"문서 삭제 완료: {doc_id}")

if __name__ == "__main__":
    print("ChromaDB 연결 확인 중...")
    col = get_or_create_collection()
    print(f"컬렉션 준비 완료: {col.name}")