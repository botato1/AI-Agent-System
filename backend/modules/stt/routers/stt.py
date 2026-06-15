import os
import uuid
import wave
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from ..services.pipeline import process_audio_pipeline
from ..utils.file_handler import save_upload_file
from ..core.config import UPLOAD_DIR, logger

router = APIRouter()

def get_audio_duration(wav_path: str) -> float:
    """WAV 오디오 파일의 실제 길이를 초(sec) 단위로 계산하는 헬퍼 함수"""
    try:
        with wave.open(wav_path, 'r') as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            duration = frames / float(rate)
            return round(duration, 2)
    except Exception as e:
        logger.error(f"⚠️ 오디오 길이 계산 실패: {e}")
        return 0.0


@router.post("/stt")
async def stt_endpoint(
    file: UploadFile = File(...),
    topic: str = Form("")
):
    """
    업로드된 오디오 파일을 분석하여 텍스트를 추출(Whisper)하고 화자를 분리(Pyannote)합니다.
    최종 결과물은 팀 공통 Document 통합 스키마 규격에 맞춰 반환됩니다.
    """
    try:
        logger.info(f"📥 새로운 오디오 업로드 수신: {file.filename}")
        
        # 1. 파일 임시 저장 및 FFmpeg 16kHz WAV 정규화 전처리
        save_path = save_upload_file(file)
        
        # 문서 식별용 메타데이터 추출
        doc_id = str(uuid.uuid4())
        doc_title = os.path.splitext(file.filename)[0]
        original_ext = os.path.splitext(file.filename)[1]
        
        # 2. 정제된 WAV 파일로부터 실제 오디오 길이(초) 계산
        actual_duration = get_audio_duration(save_path)
        
        # 3. 메인 가속 파이프라인 가동 (STT 텍스트 + 화자 타임스탬프 결합)
        transcription_result = process_audio_pipeline(save_path, topic)
        
        # 4. 팀 규약 5번 준수: 전체 대사 배열을 공백 기준으로 병합하여 단일 content 생성
        full_content = " ".join([seg["text"] for seg in transcription_result])
        
        # 5. 프론트엔드 오디오 재생 컴포넌트 스트리밍을 위한 정적 자원 URL 주소 생성
        filename = os.path.basename(save_path)
        file_url = f"http://localhost:8001/uploads/{filename}"
        
        # 6. 공통 스키마 규격 충족 데이터 하이브리드 빌드
        response_schema = {
          "status": "success",
          "data": {
            # 🔒 필수 공통 키 (14개)
            "id": doc_id,
            "title": doc_title,
            "type": "voice",
            "source": "voice",
            "content": full_content,
            "summary": "",  # LLM/RAG 파트 엔지니어가 채울 수 있도록 구조 개방
            "language": "ko",
            "created_at": datetime.utcnow().isoformat() + "Z",  # ISO 8601 표준 규격
            "tags": ["voice_upload"],
            "status": "processed",
            "notion_url": None,  # 💡 null -> None 수정 완료
            "chroma_id": None,   # 💡 null -> None 수정 완료
            "error": None,       # 💡 null -> None 수정 완료
            "user_edited": False,  # 루트 문서 수정 플래그 초기화
            
            # 🎧 이준오 전용 모듈 특화 확장 키
            "transcription": transcription_result,
            "metadata": {
              "duration_sec": actual_duration,
              "original_format": original_ext,
              "model_used": "large-v3-turbo",
              "vad_applied": True,
              "initial_prompt_applied": True,
              "total_time_sec": 0.0,  # 서비스 프로파일링 고도화 시 연동 가능
              "compute_type": "int8",
              "original_file_url": file_url
            }
          },
          "message": "음성 인식 및 화자 분리가 완료되었습니다.",
          "error": None  # 💡 null -> None 수정 완료
        }
        
        return response_schema

    except Exception as e:
        logger.error(f"❌ STT 라우터 내부 치명적 파이프라인 에러: {str(e)}")
        return {
            "status": "error",
            "data": {
                "id": str(uuid.uuid4()),
                "status": "error",
                "error": str(e)
            },
            "message": "음성 처리 파이프라인 연산 중 내부 서버 에러가 발생했습니다.",
            "error": str(e)
        }


@router.get("/list")
async def get_audio_files_list():
    """서버 스토리지(uploads 폴더) 내에 적재 보관된 모든 정제 음성 자원 목록을 내림차순 조회합니다."""
    try:
        if not os.path.exists(UPLOAD_DIR):
            return {"status": "success", "count": 0, "data": [], "error": None} # 💡 null -> None 수정 완료

        file_list = []
        for filename in os.listdir(UPLOAD_DIR):
            if filename.lower().endswith(('.wav', '.m4a', '.mp3')):
                file_path = os.path.join(UPLOAD_DIR, filename)
                file_url = f"http://localhost:8001/uploads/{filename}"
                file_size_mb = round(os.path.getsize(file_path) / (1024 * 1024), 2)
                created_time = os.path.getctime(file_path)
                
                file_list.append({
                    "filename": filename,
                    "url": file_url,
                    "size_mb": file_size_mb,
                    "created_at": datetime.fromtimestamp(created_time).isoformat() + "Z"
                })
                
        # 최신 업로드/생성 파일 우선 배치를 위한 내림차순 정렬
        file_list.sort(key=lambda x: x["created_at"], reverse=True)

        return {
            "status": "success",
            "count": len(file_list),
            "data": file_list,
            "error": None # 💡 null -> None 수정 완료
        }

    except Exception as e:
        logger.error(f"❌ 음성 리소스 스토리지 조회 실패: {str(e)}")
        return {
            "status": "error",
            "count": 0,
            "data": [],
            "error": str(e)
        }