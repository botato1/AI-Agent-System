import os
import uuid
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form
from ..services.pipeline import process_audio_pipeline
from ..utils.file_handler import save_upload_file
from ..core.config import logger

router = APIRouter()

@router.post("/stt")
async def stt_endpoint(
    file: UploadFile = File(...),
    topic: str = Form("")
):
    try:
        # 1. 오디오 파일 임시 저장 및 WAV 전처리
        save_path = save_upload_file(file)
        
        # 문서 고유 UUID 생성 및 파일명 추출 (확장자 분리)
        doc_id = str(uuid.uuid4())
        doc_title = os.path.splitext(file.filename)[0]
        original_ext = os.path.splitext(file.filename)[1]
        
        # 2. 메인 파이프라인 실행 (STT + 화자 분리)
        # (각 대사마다 "user_edited": False가 포함되어 나옵니다)
        transcription_result = process_audio_pipeline(save_path, topic)
        
        # 3. 팀 공통 규약: 모든 대사를 하나의 String으로 병합하여 content 생성
        full_content = " ".join([seg["text"] for seg in transcription_result])
        
        # 4. 정적 파일 접근용 외부 URL 생성 (프론트엔드 오디오 재생용)
        # save_path에서 파일명만 추출 (예: audio_1234abcd.wav)
        filename = os.path.basename(save_path)
        file_url = f"http://localhost:8001/uploads/{filename}" 
        # (실제 대학교 서버 배포 시 localhost를 서버의 IP나 도메인으로 변경하세요)
        
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
                "summary": "",  # 메인 백엔드/LLM에서 채울 공간
                "language": "ko",
                "created_at": datetime.utcnow().isoformat() + "Z", # ISO 8601 표준
                "tags": ["voice_upload"],
                "status": "processed",
                "notion_url": None,
                "chroma_id": None,
                "error": None,
                "user_edited": False, # 루트 레벨 전체 문서 수정 여부
                
                # 🎧 이준오 전용 키 (모듈 특화 데이터)
                "transcription": transcription_result,
                "metadata": {
                    "duration_sec": 0.0, # 추후 실제 길이 계산 로직 연결 시 업데이트
                    "original_format": original_ext,
                    "model_used": "large-v3-turbo",
                    "vad_applied": True,
                    "initial_prompt_applied": True,
                    "total_time_sec": 0.0, # 추후 성능 측정 시간 연결 시 업데이트
                    "compute_type": "int8",
                    "original_file_url": file_url # 🔗 프론트엔드 직접 접근 URL
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