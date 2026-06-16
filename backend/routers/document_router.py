# 문서 관련 API 엔드포인트
from fastapi import APIRouter, UploadFile, File, Form

from backend.services.document_service import upload_and_process_document
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
# 8003 문서 처리 서버에서 받은 document_id와 문서 정보를 8000 서버 DB에 저장
@router.post("/metadata")
def save_document_metadata_api(request: DocumentMetadataSaveRequest):
    try:
        # 1. 채팅방 생성 또는 갱신
        ensure_conversation(
            conversation_id=request.room_id,
            title=request.filename,
        )

        # 2. 문서 유형에 따라 source 값 설정
        # 일반 문서/회의록 문서는 pdf, 음성 회의록은 voice로 저장
        source = "voice" if request.type == "voice" else "pdf"

        # 3. 8003에서 받은 document_id를 그대로 documents.id에 저장
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


# 기존 문서 업로드 API
# 실제 경로: POST /api/documents/upload
# TODO: 문서 업로드/처리는 8003 POST /api/document로 이관 예정
# 이관이 완전히 끝나기 전까지 기존 API 유지
@router.post("/upload")
async def upload_document(file: UploadFile = File(...), room_id: str = Form(...)):
    return await upload_and_process_document(
        file=file,
        room_id=room_id
    )