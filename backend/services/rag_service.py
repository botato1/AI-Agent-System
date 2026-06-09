import sys
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from backend.modules.rag.chroma_client import search_hybrid

def get_utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def is_rag_result_relevant(rag_result: dict, min_score: float = 0.5) -> bool:
    """RAG 검색 결과가 충분히 관련있는지 판단"""
    if rag_result.get("status") != "success":
        return False
    if rag_result.get("count", 0) == 0:
        return False
    data = rag_result.get("data", [])
    if not data:
        return False
    top_score = data[0].get("score", 0)
    return top_score >= min_score

class RAGService:

    @staticmethod
    def retrieve_relevant_knowledge(
        query: str,
        original_query: str = None,	
        top_k: int = 5,
        relative_threshold: float = 0.5,
        filter: dict = None
    ):
        """
        하이브리드 검색 (BGE-M3 벡터 + 키워드)
        → 상대평가 필터링
        → 공통키 + 문서 식별 필드 반환

        filter 예시
        → {"type": "meeting"}           회의록만
        → {"document_id": "uuid"}       특정 문서만
        → {"filename": "회의록.pdf"}    특정 파일만
        → {"upload_context": "document"} 문서 업로드만
        """
        print(f"[RAG Service] 쿼리: '{query}'")

        try:
            raw_results = search_hybrid(
                query_text=query,
                top_k=top_k,
                filter=filter
            )

            if not raw_results:
                return {
                    "status": "success",
                    "query": query,
                    "count": 0,
                    "data": [],
                    "error": None
                }

            max_score = raw_results[0]["score"]
            min_absolute_bound = 0.1
            processed_documents = []

            for res in raw_results:
                relative_ratio = res["score"] / max_score if max_score > 0 else 0

                if res["score"] < min_absolute_bound or relative_ratio < relative_threshold:
                    print(f"[탈락] 점수: {res['score']}")
                    continue

                meta = res["metadata"]

                processed_documents.append({
                    "id": res["id"],
                    "content": res["document"],
                    "title": meta.get("title", "제목 없음"),
                    "type": meta.get("type", "document"),
                    "source": meta.get("source", ""),
                    "language": meta.get("language", "ko"),
                    "created_at": meta.get("created_at", get_utc_now()),
                    "status": meta.get("status", "processed"),
                    "notion_url": meta.get("notion_url", ""),
                    "chroma_id": meta.get("chroma_id", ""),
                    "error": meta.get("error", ""),
                    "user_edited": meta.get("user_edited", False),
                    "tags": meta.get("tags", ""),
                    "importance_score": meta.get("importance_score", 0),
                    "score": res["score"],
                    "document_id": meta.get("document_id", ""),
                    "filename": meta.get("filename", ""),
                    "chunk_index": meta.get("chunk_index", 0),
                    "upload_context": meta.get("upload_context", ""),
                    "room_id": meta.get("room_id", ""),
                })

            print(f"[RAG Service] 완료 → {len(processed_documents)}개 반환 (최고점: {max_score})")

            return {
                "status": "success",
                "query": query,
                "count": len(processed_documents),
                "data": processed_documents,
                "error": None
            }

        except Exception as e:
            print(f"[RAG Service 에러]: {str(e)}")
            return {
                "status": "error",
                "query": query,
                "count": 0,
                "data": [],
                "error": f"RAG 파이프라인 장애: {str(e)}"
            }

rag_service = RAGService()