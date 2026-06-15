# 문서 업로드 및 처리 서비스
import os
from pathlib import Path
from fastapi import UploadFile
import httpx

from backend.modules.rag.document_loader import load_and_insert
from backend.db.crud import ensure_conversation, save_document_metadata

STT_URL = os.getenv("STT_URL", "http://192.168.0.245:8001/api/stt")
OCR_URL = os.getenv("OCR_URL", "http://localhost:8003/process")


# TODO: 문서/음성 처리 담당자와 최종 지원 확장자 확정 필요
# 현재는 테스트 및 임시 연동을 위한 허용 목록
ALLOWED_DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".png", ".jpg", ".jpeg",
}

# 프로젝트 루트 기준 data/raw 경로
BASE_DIR = Path(__file__).resolve().parents[2]
UPLOAD_DIR = BASE_DIR / "data" / "raw"


def is_allowed_document_file(file: UploadFile) -> bool:
    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()

    if suffix in ALLOWED_DOCUMENT_EXTENSIONS:
        return True

    if file.content_type and file.content_type.startswith("audio/"):
        return True

    return False


def _get_document_type(filename: str, content_type: str | None) -> str:
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        return "document"

    if suffix in {".png", ".jpg", ".jpeg"}:
        return "image"

    if content_type and content_type.startswith("audio/"):
        return "voice"

    return "document"


def _get_source(filename: str, content_type: str | None) -> str:
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        return "pdf"

    if suffix in {".png", ".jpg", ".jpeg"}:
        return "image"

    if content_type and content_type.startswith("audio/"):
        return "voice"

    return suffix.replace(".", "") or "file"


# 문서 업로드 후 임시로 ChromaDB에 적재하는 함수
# TODO : 문서 처리 코드 완성 후 텍스트 추출/요약/할 일 등 결과를 받아 저장하는 구조로 변경
async def upload_and_process_document(file: UploadFile, room_id: str) -> dict:
    try:
        filename = Path(file.filename).name

        # 1. 파일 형식 검사
        if not is_allowed_document_file(file):
            return {
                "status": "error",
                "room_id": room_id,
                "filename": file.filename,
                "saved_path": None,
                "message": "지원하지 않는 파일 형식입니다.",
                "error": "unsupported_file_type"
            }

        # 2. 업로드 폴더가 없으면 생성
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        # 3. 파일 저장 경로 생성
        save_path = UPLOAD_DIR / filename

        # 4. 업로드된 파일 내용 읽기
        file_content = await file.read()

        # 5. 파일 저장
        with open(save_path, "wb") as f:
            f.write(file_content)

        # 6. 파일 형식에 따라 처리 분기
        suffix = Path(filename).suffix.lower()
        document_type = _get_document_type(filename, file.content_type)
        source = _get_source(filename, file.content_type)
        stt_result = None
        ocr_result = None

        if suffix == ".pdf":
            load_and_insert(str(save_path))
            message = "문서 업로드 및 ChromaDB 적재 완료"

        elif suffix in {".png", ".jpg", ".jpeg"}:
            try:
                async with httpx.AsyncClient(timeout=180.0) as client:
                    with open(save_path, "rb") as img_file:
                        response = await client.post(
                            OCR_URL,
                            files={"file": (filename, img_file, file.content_type)},
                        )
                    ocr_result = response.json()
                message = "이미지 OCR 처리 완료"
            except Exception as ocr_error:
                ocr_result = None
                message = f"이미지 업로드 완료, OCR 처리 실패: {str(ocr_error)}"

        elif file.content_type and file.content_type.startswith("audio/"):
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    with open(save_path, "rb") as audio_file:
                        response = await client.post(
                            STT_URL,
                            files={"file": (filename, audio_file, file.content_type)},
                            data={"topic": ""},
                        )
                    stt_result = response.json()
                message = "음성 파일 STT 처리 완료"
            except Exception as stt_error:
                stt_result = None
                message = f"음성 업로드 완료, STT 처리 실패: {str(stt_error)}"

        else:
            message = "파일 업로드 완료"

        # 7. 업로드만 해도 채팅방 목록에 나오도록 conversations 생성/갱신
        ensure_conversation(room_id, filename)

        # 8. GET /api/conversations에서 filename을 반환할 수 있도록 documents 테이블에 저장
        document_id = save_document_metadata({
            "conversation_id": room_id,
            "title": filename,
            "type": document_type,
            "source": source,
            "file_path": str(save_path),
            "summary": str(stt_result or ocr_result) if (stt_result or ocr_result) else "",
            "status": "processed",
            "notion_url": "",
            "error": "",
        })

        # 9. 성공 결과 반환
        return {
            "status": "success",
            "room_id": room_id,
            "document_id": document_id,
            "filename": filename,
            "saved_path": str(save_path),
            "message": message,
            "error": None
        }

    except Exception as e:
        return {
            "status": "error",
            "room_id": room_id,
            "filename": file.filename if file else None,
            "saved_path": None,
            "message": "문서 업로드 또는 처리 중 오류가 발생했습니다.",
            "error": str(e)
        }