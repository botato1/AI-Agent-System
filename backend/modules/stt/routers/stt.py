# routers/stt.py
import os
import time
import tempfile
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

# 분리된 서비스 모듈 가져오기
from services.audio_service import convert_to_wav
from services.ai_service import process_audio_with_ai

router = APIRouter(prefix="/api/v1")

@router.post("/stt")
async def process_audio(
    file: UploadFile = File(...),
    topic: str = Form("일반 회의")  # 💡 대화 주제(Topic) 칸 부활!
):
    print(f"📥 [요청 수신] 파일명: {file.filename}, 주제: {topic}")
    start_time = time.time()
    
    _, file_extension = os.path.splitext(file.filename)
    temp_input_path = ""
    wav_path = ""

    try:
        # 1. 업로드된 원본 파일 임시 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension.lower()) as temp_input:
            temp_input.write(await file.read())
            temp_input_path = temp_input.name

        # 2. 오디오 변환 서비스 호출 (16kHz, Mono 변환)
        wav_path = convert_to_wav(temp_input_path)

        # 3. AI 모델 서비스 호출 (화자분리 + STT 병합 로직)
        transcription_result = process_audio_with_ai(wav_path, topic)

    except Exception as e:
        print(f"❌ [에러 발생] {str(e)}")
        raise HTTPException(status_code=500, detail=f"오류 발생: {str(e)}")
    
    finally:
        # 4. 임시 파일 청소 (원본 파일, 변환된 wav 파일 모두 삭제)
        if temp_input_path and os.path.exists(temp_input_path):
            os.remove(temp_input_path)
        if wav_path and os.path.exists(wav_path):
            os.remove(wav_path)

    process_time = time.time() - start_time
    print(f"📤 [분석 완료] 소요 시간: {process_time:.2f}초")

    return JSONResponse(content={
        "file_info": {
            "file_name": file.filename,
            "topic_applied": topic
        },
        "status": "success",
        "transcription": transcription_result
    })