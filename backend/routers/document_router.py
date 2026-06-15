# 문서 업로드 관련 API 엔드포인트
from fastapi import APIRouter, UploadFile, File, Form

from backend.services.document_service import upload_and_process_document
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
            "created_at": row["created_at"],
        }
        for row in rows
    ]

    return {
        "status": "success",
        "documents": documents,
        "error": None,
    }


# 문서 업로드 API
# 실제 경로: POST /api/documents/upload
# 프론트에서 FormData로 file과 room_id를 받아서 document_service에 처리를 맡김
@router.post("/upload")
async def upload_document(file: UploadFile = File(...), room_id: str = Form(...)):
    return await upload_and_process_document(
        file=file,
        room_id=room_id
    )