"""FastAPI 서버 — PDF 업로드 → 문서처리 파이프라인 → JSON 반환"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

# 저장 경로 (repo 루트 기준)
_REPO_ROOT     = Path(__file__).parent.parent.parent  # AI-Agent-System/
_STORAGE_DIR   = _REPO_ROOT / "storage" / "uploads" / "documents"
_DATA_DIR      = _REPO_ROOT / "data" / "uploads" / "documents"

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import chromadb

from doc_processor.core.pipeline import DocumentPipeline
from doc_processor.output.assembler import assemble

# ChromaDB 클라이언트 (연결 실패 시 None)
try:
    _chroma = chromadb.HttpClient(host="localhost", port=8001)
except Exception as e:
    print(f"[ChromaDB] 연결 실패 (저장 비활성화): {e}")
    _chroma = None


def _save_to_chroma(out: dict) -> None:
    """chunks를 ChromaDB documents 컬렉션에 저장합니다."""
    if _chroma is None:
        print("[ChromaDB] 클라이언트 없음, 저장 스킵")
        return
    chunks = out.get("chunks", [])
    if not chunks:
        return

    collection = _chroma.get_or_create_collection("documents")

    ids       = [c["id"] for c in chunks]
    documents = [c.get("content", "") for c in chunks]
    metadatas = [
        {
            "document_id": out.get("document_id", ""),
            "filename":    out.get("filename", ""),
            "page_number": c.get("page_number", 0),
            "type":        c.get("type", "text"),
        }
        for c in chunks
    ]

    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    print(f"[ChromaDB] {len(ids)}개 chunks 저장 완료")

app = FastAPI(title="Document Processor API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 파이프라인 싱글톤 (서버 시작 시 1회 로드)
_pipeline: DocumentPipeline | None = None


def get_pipeline() -> DocumentPipeline:
    global _pipeline
    if _pipeline is None:
        print("[Server] 파이프라인 초기화 중...")
        _pipeline = DocumentPipeline()
        print("[Server] 파이프라인 준비 완료")
    return _pipeline


@app.on_event("startup")
async def startup():
    get_pipeline()


@app.get("/health")
def health():
    """서버 상태 확인"""
    return {"status": "ok"}


@app.post("/api/document")
async def process_pdf(file: UploadFile = File(...)):
    """
    PDF 파일을 업로드하면 문서처리 결과를 JSON으로 반환합니다.

    - **file**: PDF 파일
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다.")

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        start = time.time()
        pipeline = get_pipeline()

        doc_result = pipeline.run(tmp_path)
        assembled  = assemble(doc_result)
        elapsed    = round(time.time() - start, 2)

        # 원본 PDF 저장
        _STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        saved_pdf = _STORAGE_DIR / file.filename
        shutil.copy2(tmp_path, saved_pdf)

        out = assembled.model_dump(mode="json") if hasattr(assembled, "model_dump") else assembled.__dict__

        # 처리 시간 추가
        if isinstance(out.get("metadata"), dict):
            out["metadata"]["api_processing_time_sec"] = elapsed

        # 팀 공통 스키마 필드 추가
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        out.setdefault("type", "document")
        out.setdefault("summary", out.get("content", "")[:200] if out.get("content") else "")
        out.setdefault("language", "ko")
        out.setdefault("created_at", now)
        out.setdefault("importance_score", 0)
        out.setdefault("related_documents", [])
        out.setdefault("notion_url", None)
        out.setdefault("chroma_id", None)
        out.setdefault("error", None)
        out.setdefault("user_edited", False)

        # 프론트 채팅 연동용
        out["document_id"] = out.get("id")
        out["filename"] = file.filename

        # 추출 JSON 저장
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        json_filename = Path(file.filename).stem + ".json"
        saved_json = _DATA_DIR / json_filename
        saved_json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

        # ChromaDB 저장
        try:
            _save_to_chroma(out)
        except Exception as e:
            print(f"[ChromaDB] 저장 실패 (무시): {e}")

        return JSONResponse(content=out)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8003, reload=False)
