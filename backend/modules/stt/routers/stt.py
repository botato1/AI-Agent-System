import os
import uuid
import wave  # 💡 내장 오디오 처리 모듈 추가
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form
from ..services.pipeline import process_audio_pipeline
from ..utils.file_handler import save_upload_file
from ..core.config import logger

router = APIRouter()

# 💡 WAV 파일의 실제 길이를 초(sec) 단위로 계산하는 헬퍼 함수
def get_audio_duration(wav_path: str) -> float:
    try:
        with wave.open(wav_path, 'r') as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            duration = frames / float(rate)
            return round(duration, 2)
    except Exception as e:
        logger.error(f"오디오 길이 계산 실패: {e}")
        return 0.0

@router.post("/stt")
async def stt_endpoint(
    file: UploadFile = File(...),
    topic: str = Form("")
):
    try:
        # 1. 오디오 파일 임시 저장 및 WAV 전처리
        save_path = save_upload_file(file)
        
        # 문서 고유 UUID 생성 및 파일명 추출
        doc_id = str(uuid.uuid4())
        doc_title = os.path.splitext(file.filename)[0]
        original_ext = os.path.splitext(file.filename)[1]
        
        # 💡 1.5 추가: 정제된 WAV 파일의 실제 오디오 길이 계산 (초 단위)
        actual_duration = get_audio_duration(save_path)
        
        # 2. 메인 파이프라인 실행 (STT + 화자 분리)
        transcription_result = process_audio_pipeline(save_path, topic)
        
        # 3. 팀 공통 규약: 모든 대사를 하나의 String으로 병합
        full_content = " ".join([seg["text"] for seg in transcription_result])
        
        # 4. 정적 파일 접근용 외부 URL 생성
        filename = os.path.basename(save_path)
        file_url = f"http://localhost:8001/uploads/{filename}" 
        
        # 5. 완벽한 통합 JSON 스키마 규격으로 응답 포장
        response_schema = {
            "status": "success",
            "data": {
                # 🔒 필수 공통 키 (14개)
                "id": doc_id,
                "title": doc_title,
                "type": "voice",
                "source": "voice",
                "content": full_content,
                "summary": "",  
                "language": "ko",
                "created_at": datetime.utcnow().isoformat() + "Z", 
                "tags": ["voice_upload"],
                "status": "processed",
                "notion_url": None,
                "chroma_id": None,
                "error": None,
                "user_edited": False, 
                
                # 🎧 이준오 전용 키
                "transcription": transcription_result,
                "metadata": {
                    "duration_sec": actual_duration, # 🔗 실제 오디오 길이 매핑 완료!
                    "original_format": original_ext,
                    "model_used": "large-v3-turbo",
                    "vad_applied": True,
                    "initial_prompt_applied": True,
                    "total_time_sec": 0.0, # (API 처리 소요 시간 기능 추가 시 업데이트 필요)
                    "compute_type": "int8",
                    "original_file_url": file_url 
                }
            }
        }
        
        return response_schema

    except Exception as e:
        logger.error(f"STT API 에러: {str(e)}")
        return {
            "status": "error",
            "data": {
                "id": str(uuid.uuid4()),
                "error": str(e),
                "status": "error"
            }
        }