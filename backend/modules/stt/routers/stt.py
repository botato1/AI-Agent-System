from fastapi import APIRouter, UploadFile, File, Form
from ..services.pipeline import process_audio_pipeline
from ..utils.file_handler import save_upload_file

router = APIRouter()

@router.post("/stt")
async def stt_endpoint(
    file: UploadFile = File(...),
    topic: str = Form("")
):
    # 1. 파일 저장 (유틸리티 사용)
    save_path = save_upload_file(file)
    
    # 2. 메인 파이프라인 실행 (로직 은닉화)
    result = process_audio_pipeline(save_path, topic)
    
    # 3. 결과 반환
    return {"status": "success", "data": result}