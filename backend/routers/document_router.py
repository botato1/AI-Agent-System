# 문서 관련 API 엔드포인트
from typing import Literal

from fastapi import APIRouter, UploadFile, File, Form

from backend.services.document_service import (
    upload_and_process_document,
    delete_processed_document,
    get_document_detail,
)
from backend.db.crud import get_all_documents

router = APIRouter(
    prefix="/api/documents",
    tags=["Documents"]
)

# 업로드된 전체 문서 목록 조회 API
# 실제 경로: GET /api/documents
@router.get("")
def get_document_list():
    rows = get_all_documents()

    documents = [
        {
            "document_id": row["document_id"],
            "filename": row["filename"],
            "room_id": row["room_id"],
            "type": row.get("type"),
            "json_path": row.get("json_path"),
            "created_at": row["created_at"],
        }
        for row in rows
    ]

    return {
        "status": "success",
        "documents": documents,
        "error": None,
    }

# 문서 업로드 통합 API
# 실제 경로: POST /api/documents/upload
# 프론트는 이 API만 호출
# 문서 파일은 8003 문서 처리 서버로 전달하고,
# 음성 파일은 기존 STT 처리 흐름을 유지한다.
@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    room_id: str | None = Form(None),
    document_type: Literal["document", "meeting"] = Form("document", alias="type"),
):
    return await upload_and_process_document(
        file=file,
        room_id=room_id,
        document_type=document_type,
    )


# 문서 상세 조회 API
# 실제 경로: GET /api/documents/{document_id}
# 문서 보관함에서 문서 1개 클릭 시 사용
@router.get("/{document_id}")
def get_document_detail_api(document_id: str):
    return get_document_detail(document_id)


# 문서 삭제 API
# 실제 경로: DELETE /api/documents/{document_id}
@router.delete("/{document_id}")
def delete_document_api(document_id: str):
    return delete_processed_document(document_id)