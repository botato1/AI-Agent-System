# 문서 업로드 관련 API 엔드포인트
from fastapi import APIRouter, UploadFile, File, Form

from backend.services.document_service import upload_and_process_document


router = APIRouter(
    prefix="/api/documents",
    tags=["Documents"]
)


# 문서 업로드 API
# 프론트에서 FormData로 file과 room_id를 받아서 document_service에 처리를 맡김
@router.post("/upload")
async def upload_document(file: UploadFile = File(...), room_id: str = Form(...)):
    return await upload_and_process_document(
        file=file,
        room_id=room_id
    )