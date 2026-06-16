import os
import uuid
import wave
import json
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
    """오디오 파일을 수신하여 분석(STT+화자분리)하고, 결과를 JSON 파일로 서버에 영구 보관합니다."""
    try:
        logger.info(f"📥 새로운 오디오 업로드 수신: {file.filename}")
        
        # 1. 파일 임시 저장 및 FFmpeg 16kHz WAV 전처리
        save_path = save_upload_file(file)
        
        # 고유 식별자 발급 및 파일명 가공
        doc_id = str(uuid.uuid4())
        doc_title = os.path.splitext(file.filename)[0]
        original_ext = os.path.splitext(file.filename)[1]
        
        # 2. 실제 오디오 재생 시간 추출
        actual_duration = get_audio_duration(save_path)
        
        # 3. AI 파이프라인 구동 (Whisper + Pyannote)
        transcription_result = process_audio_pipeline(save_path, topic)
        
        # 4. 모든 문장을 하나로 병합한 content 생성
        full_content = " ".join([seg["text"] for seg in transcription_result])
        
        # 4-5. RAG/LLM 팀을 위한 텍스트 조각(Chunk) 리스트 생성
        chunks_list = [seg["text"] for seg in transcription_result]
        
        # 5. 정적 오디오 스트리밍용 외부 접근 URL 생성
        filename = os.path.basename(save_path)
        file_url = f"http://localhost:8001/uploads/{filename}"
        
        # 6. 팀 통합 공통 스키마 빌드
        response_schema = {
            "status": "success",
            "data": {
                "id": doc_id,
                "title": doc_title,
                "type": "voice",
                "source": "voice",
                "content": full_content,
                "chunks": chunks_list,
                "summary": "",
                "language": "ko",
                "created_at": datetime.utcnow().isoformat() + "Z",
                "tags": ["voice_upload"],
                "status": "processed",
                "notion_url": None,
                "chroma_id": None,
                "error": None,
                "user_edited": False,
                
                "transcription": transcription_result,
                "metadata": {
                    "duration_sec": actual_duration,
                    "original_format": original_ext,
                    "model_used": "large-v3-turbo",
                    "vad_applied": True,
                    "initial_prompt_applied": True,
                    "total_time_sec": 0.0,
                    "compute_type": "int8",
                    "original_file_url": file_url
                }
            },
            "message": "음성 인식 및 화자 분리가 완료되었습니다.",
            "error": None
        }
        
        # 7. 분석 결과를 추후 재조회 할 수 있도록 JSON 파일로 저장
        file_core_name = os.path.splitext(filename)[0] 
        result_json_path = os.path.join(UPLOAD_DIR, f"result_{file_core_name}.json")
        
        with open(result_json_path, "w", encoding="utf-8") as f:
            json.dump(response_schema, f, ensure_ascii=False, indent=2)
            
        logger.info(f"💾 STT 분석 결과 저장 완료: result_{file_core_name}.json")
        return response_schema

    except Exception as e:
        logger.error(f"❌ STT 라우터 에러: {str(e)}")
        return {"status": "error", "message": "내부 서버 에러", "error": str(e)}


@router.get("/stt/{file_id}")
async def get_stt_result_detail(file_id: str):
    """과거에 분석이 완료된 특정 파일의 상세 결과를 재조회합니다."""
    try:
        clean_file_id = file_id.replace("result_", "") 
        result_json_filename = f"result_{clean_file_id}.json"
        result_json_path = os.path.join(UPLOAD_DIR, result_json_filename)
        
        if not os.path.exists(result_path := result_json_path):
            raise HTTPException(
                status_code=404, 
                detail="해당 파일의 STT 분석 결과를 찾을 수 없습니다. 먼저 분석(/api/stt)을 진행하세요."
            )
            
        with open(result_path, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
            
        return saved_data

    except HTTPException as http_ext:
        raise http_ext
    except Exception as e:
        logger.error(f"❌ 상세 결과 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"서버 내부 오류: {str(e)}")


@router.get("/list")
async def get_audio_files_list():
    """서버 스토리지(uploads 폴더) 내에 보관된 음성 파일 리스트를 가져옵니다."""
    try:
        if not os.path.exists(UPLOAD_DIR):
            return {"status": "success", "count": 0, "data": [], "error": None}

        file_list = []
        for filename in os.listdir(UPLOAD_DIR):
            if filename.lower().endswith(('.wav', '.m4a', '.mp3')):
                file_path = os.path.join(UPLOAD_DIR, filename)
                file_url = f"http://localhost:8001/uploads/{filename}"
                file_size_mb = round(os.path.getsize(file_path) / (1024 * 1024), 2)
                created_time = os.path.getctime(file_path)
                
                file_id = os.path.splitext(filename)[0]
                
                file_list.append({
                    "file_id": file_id, 
                    "filename": filename,
                    "url": file_url,
                    "size_mb": file_size_mb,
                    "created_at": datetime.fromtimestamp(created_time).isoformat() + "Z"
                })
                
        file_list.sort(key=lambda x: x["created_at"], reverse=True)
        return {"status": "success", "count": len(file_list), "data": file_list, "error": None}

    except Exception as e:
        return {"status": "error", "count": 0, "data": [], "error": str(e)}