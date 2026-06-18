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
# 실제 경로: POST /api/stt/upload
# 프론트는 음성 파일 업로드 시 이 API를 호출한다.
# 8000 서버가 받은 음성 파일을 8001 STT 서버로 전달하고,
# STT 결과를 받아 documents / document_chunks 테이블에 저장한다.
@router.post("/upload")
async def upload_stt_file(
    file: UploadFile = File(...),
    room_id: str = Form(...),
):
    return await upload_and_process_stt(
        file=file,
        room_id=room_id,
    )


# STT 음성 목록 조회 API
# 실제 경로: GET /api/stt/list
# 업로드된 모든 음성 파일 목록을 조회한다.
# 8001 서버를 다시 호출하지 않고,
# 8000 DB의 documents 테이블에서 type='voice' 데이터 전체를 조회한다.
@router.get("/list")
def get_stt_file_list():
    return get_stt_list()


# STT 음성 상세 조회 API
# 실제 경로: GET /api/stt/{document_id}
# 특정 음성 파일의 상세 정보와 transcription 목록을 조회한다.
# 8000 DB의 documents / document_chunks 기준으로 조회한다.
@router.get("/{document_id}")
def get_stt_file_detail(
    document_id: str,
):
    return get_stt_detail(
        document_id=document_id,
    )


# STT 음성 삭제 API
# 실제 경로: DELETE /api/stt/{document_id}
# 8000 DB의 documents / document_chunks를 삭제하고,
# 8001 STT 서버의 DELETE /api/stt/{file_id}를 내부 호출해
# 원본 음성 파일과 STT 결과 JSON도 삭제한다.
# file_id는 metadata.original_file_url에서 추출한 audio_xxx 값을 우선 사용한다.
@router.delete("/{document_id}")
async def delete_stt_file(
    document_id: str,
):
    return await delete_stt_document(
        document_id=document_id,
    )