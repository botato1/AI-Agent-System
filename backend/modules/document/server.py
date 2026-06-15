"""FastAPI 서버 — PDF 업로드 → 문서처리 파이프라인 → JSON 반환"""
from __future__ import annotations

import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from doc_processor.core.pipeline import DocumentPipeline
from doc_processor.output.assembler import assemble

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


@app.post("/process")
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

        return JSONResponse(content=out)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8003, reload=False)
