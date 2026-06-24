# backend/routers/stt_router.py
# STT 관련 API 엔드포인트
from fastapi import APIRouter, UploadFile, File, Form

from backend.services.stt_upload_service import (
    upload_and_process_stt,
    get_stt_list,
    get_stt_detail,
    delete_stt_document,
)


router = APIRouter(
    prefix="/api/stt",
    tags=["STT"]
)


# STT 업로드 API
@router.post("/upload")
async def upload_stt_file(
    file: UploadFile = File(...),
    room_id: str | None = Form(None),
):
    return await upload_and_process_stt(
        file=file,
        room_id=room_id,
    )


# STT 음성 목록 조회 API
@router.get("/list")
def get_stt_file_list():
    return get_stt_list()


# STT 음성 상세 조회 API
@router.get("/{document_id}")
def get_stt_file_detail(
    document_id: str,
):
    return get_stt_detail(
        document_id=document_id,
    )


# STT 음성 삭제 API
@router.delete("/{document_id}")
async def delete_stt_file(
    document_id: str,
):
    return await delete_stt_document(
        document_id=document_id,
    )