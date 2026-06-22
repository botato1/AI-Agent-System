# 문서 관련 API 엔드포인트
from typing import Literal

from fastapi import APIRouter, UploadFile, File, Form

from backend.services.document_service import upload_and_process_document,delete_processed_document

from backend.db.crud import (
    get_all_documents,
    ensure_conversation,
    save_document_metadata,
)
from backend.schemas.document_schema import DocumentMetadataSaveRequest


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


# 문서 메타데이터 저장 API
# 실제 경로: POST /api/documents/metadata
# 현재는 테스트/내부용 API
# 실제 프론트 문서 업로드 흐름에서는 POST /api/documents/upload 사용
@router.post("/metadata")
def save_document_metadata_api(request: DocumentMetadataSaveRequest):
    try:
        # 1. 채팅방 생성 또는 갱신
        ensure_conversation(
            conversation_id=request.room_id,
            title=request.filename,
        )

        # 2. 문서 유형에 따라 source 값 설정
        source = "voice" if request.type == "voice" else "pdf"

        # 3. 8003 또는 외부 처리 서버에서 받은 document_id를 그대로 documents.id에 저장
        saved_document_id = save_document_metadata({
            "id": request.document_id,
            "conversation_id": request.room_id,
            "title": request.filename,
            "type": request.type,
            "source": source,
            "file_path": request.file_path or "",
            "json_path": request.json_path or "",
            "content_markdown": request.content_markdown or "",
            "summary": request.summary or "",
            "status": "processed",
            "notion_url": "",
            "error": "",
        })

        return {
            "status": "success",
            "document_id": saved_document_id,
            "filename": request.filename,
            "room_id": request.room_id,
            "message": "문서 메타데이터가 저장되었습니다.",
            "error": None,
        }

    except Exception as e:
        return {
            "status": "error",
            "document_id": request.document_id,
            "filename": request.filename,
            "room_id": request.room_id,
            "message": "문서 메타데이터 저장 중 오류가 발생했습니다.",
            "error": str(e),
        }


# 문서 업로드 통합 API
# 실제 경로: POST /api/documents/upload
# 프론트는 이 API만 호출
# 문서 파일은 8003 문서 처리 서버로 전달하고,
# 음성 파일은 기존 STT 처리 흐름을 유지한다.
@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    room_id: str = Form(...),
    document_type: Literal["document", "meeting", "voice"] = Form("document", alias="type"),
):
    return await upload_and_process_document(
        file=file,
        room_id=room_id,
        document_type=document_type,
    )


# 문서 삭제 API
# 실제 경로: DELETE /api/documents/{document_id}
@router.delete("/{document_id}")
def delete_document_api(document_id: str):
    return delete_processed_document(document_id)