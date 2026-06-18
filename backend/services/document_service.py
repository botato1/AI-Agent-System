# 문서 업로드 및 처리 서비스
import os
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
import httpx

from backend.db.crud import ensure_conversation, save_document_metadata


# 문서 처리 서버 8003
DOCUMENT_PROCESS_URL = os.getenv(
    "DOCUMENT_PROCESS_URL",
    "http://220.90.180.93:8003/api/document"
)

# STT 서버는 추후 음성 업로드 흐름 정리 전까지 기존 처리 유지
STT_URL = os.getenv(
    "STT_URL",
    "http://192.168.0.245:8001/api/stt"
)


# 8003 문서 처리 서버에서 처리 가능한 문서 확장자
ALLOWED_DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".hwpx",
    ".png",
    ".jpg",
    ".jpeg",
}


# 기존 STT 흐름 유지를 위한 음성 확장자
ALLOWED_AUDIO_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".m4a",
    ".webm",
}


def is_document_file(file: UploadFile) -> bool:
    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()

    return suffix in ALLOWED_DOCUMENT_EXTENSIONS


def is_audio_file(file: UploadFile) -> bool:
    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()

    if suffix in ALLOWED_AUDIO_EXTENSIONS:
        return True

    if file.content_type and file.content_type.startswith("audio/"):
        return True

    return False


def _get_source(filename: str, content_type: str | None = None) -> str:
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        return "pdf"

    if suffix == ".hwpx":
        return "hwpx"

    if suffix in {".png", ".jpg", ".jpeg"}:
        return "image"

    if content_type and content_type.startswith("audio/"):
        return "voice"

    return suffix.replace(".", "") or "file"


def _is_valid_document_type(document_type: str) -> bool:
    return document_type in {"document", "meeting"}


# 문서 파일 처리
# 프론트에서 받은 문서 파일을 8003 문서 처리 서버로 전달하고,
# 8003 처리 결과를 documents 테이블에 저장한다.
async def _process_document_file(
    file: UploadFile,
    room_id: str,
    document_type: str,
) -> dict:
    filename = Path(file.filename).name if file.filename else "uploaded_file"

    # 1. 업로드된 파일 내용 읽기
    file_content = await file.read()

    # 2. 8003 문서 처리 서버로 파일 전달
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            DOCUMENT_PROCESS_URL,
            files={
                "file": (
                    filename,
                    file_content,
                    file.content_type or "application/octet-stream",
                )
            },
            data={
                "room_id": room_id,
                "type": document_type,
            },
        )
        
    response.raise_for_status()
    processed_result = response.json()

    # 3. 8003 처리 결과에서 필요한 값 추출
    document_id = processed_result.get("document_id")
    result_room_id = processed_result.get("room_id") or room_id
    result_filename = processed_result.get("filename") or filename
    result_type = processed_result.get("type") or document_type

    file_path = processed_result.get("file_path") or ""
    json_path = processed_result.get("json_path") or ""
    summary = processed_result.get("summary") or ""
    content_markdown = processed_result.get("content_markdown") or ""

    # 4. 필수값 검증
    if not document_id:
        return {
            "status": "error",
            "room_id": result_room_id,
            "document_id": None,
            "filename": result_filename,
            "type": result_type,
            "file_path": file_path,
            "json_path": json_path,
            "summary": summary,
            "message": "8003 문서 처리 결과에 document_id가 없습니다.",
            "error": "document_id_missing",
        }

    if not content_markdown:
        return {
            "status": "error",
            "room_id": result_room_id,
            "document_id": document_id,
            "filename": result_filename,
            "type": result_type,
            "file_path": file_path,
            "json_path": json_path,
            "summary": summary,
            "message": "8003 문서 처리 결과에 content_markdown이 없습니다.",
            "error": "content_markdown_missing",
        }

    # 5. 채팅방 생성 또는 갱신
    ensure_conversation(
        conversation_id=result_room_id,
        title=result_filename,
    )

    # 6. documents 테이블에 문서 메타데이터 저장
    saved_document_id = save_document_metadata({
        "id": document_id,
        "conversation_id": result_room_id,
        "title": result_filename,
        "type": result_type,
        "source": _get_source(result_filename, file.content_type),
        "file_path": file_path,
        "json_path": json_path,
        "content_markdown": content_markdown,
        "summary": summary,
        "status": "processed",
        "notion_url": "",
        "error": "",
    })

    # 7. 프론트에 최종 응답 반환
    return {
        "status": "success",
        "room_id": result_room_id,
        "document_id": saved_document_id,
        "filename": result_filename,
        "type": result_type,
        "file_path": file_path,
        "json_path": json_path,
        "summary": summary,
        "message": "문서 처리 및 메타데이터 저장이 완료되었습니다.",
        "error": None,
    }


# 음성 파일 처리
# 기존 STT 처리 흐름은 유지하고, 추후 음성 업로드 구조에서 별도 정리한다.
async def _process_audio_file(
    file: UploadFile,
    room_id: str,
) -> dict:
    document_id = str(uuid4())
    filename = Path(file.filename).name if file.filename else f"{document_id}.audio"

    try:
        file_content = await file.read()

        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                STT_URL,
                files={
                    "file": (
                        filename,
                        file_content,
                        file.content_type or "application/octet-stream",
                    )
                },
                data={"topic": ""},
            )

        response.raise_for_status()
        stt_result = response.json()

        ensure_conversation(
            conversation_id=room_id,
            title=filename,
        )

        saved_document_id = save_document_metadata({
            "id": document_id,
            "conversation_id": room_id,
            "title": filename,
            "type": "voice",
            "source": "voice",
            "file_path": "",
            "json_path": "",
            "content_markdown": str(stt_result),
            "summary": str(stt_result),
            "status": "processed",
            "notion_url": "",
            "error": "",
        })

        return {
            "status": "success",
            "room_id": room_id,
            "document_id": saved_document_id,
            "filename": filename,
            "type": "voice",
            "file_path": "",
            "json_path": "",
            "summary": str(stt_result),
            "message": "음성 파일 STT 처리 완료",
            "error": None,
        }

    except Exception as e:
        return {
            "status": "error",
            "room_id": room_id,
            "document_id": None,
            "filename": filename,
            "type": "voice",
            "file_path": None,
            "json_path": None,
            "summary": None,
            "message": "음성 파일 STT 처리 중 오류가 발생했습니다.",
            "error": str(e),
        }


async def upload_and_process_document(
    file: UploadFile,
    room_id: str,
    document_type: str = "document",
) -> dict:
    """
    통합 업로드 처리 함수.

    문서 파일:
    - 8003 문서 처리 서버로 전달
    - 처리 결과를 받아 documents 테이블 저장

    음성 파일:
    - 기존 STT 처리 흐름 유지
    - 추후 별도 음성 저장 구조로 개선 예정
    """
    filename = Path(file.filename).name if file and file.filename else "uploaded_file"

    try:
        # 1. 음성 파일이면 기존 STT 흐름 유지
        if is_audio_file(file):
            return await _process_audio_file(
                file=file,
                room_id=room_id,
            )

        # 2. 문서 유형 검사
        if not _is_valid_document_type(document_type):
            return {
                "status": "error",
                "room_id": room_id,
                "document_id": None,
                "filename": filename,
                "type": document_type,
                "file_path": None,
                "json_path": None,
                "summary": None,
                "message": "지원하지 않는 문서 유형입니다.",
                "error": "unsupported_document_type",
            }

        # 3. 문서 파일 확장자 검사
        if not is_document_file(file):
            return {
                "status": "error",
                "room_id": room_id,
                "document_id": None,
                "filename": filename,
                "type": document_type,
                "file_path": None,
                "json_path": None,
                "summary": None,
                "message": "지원하지 않는 파일 형식입니다.",
                "error": "unsupported_file_type",
            }

        # 4. 문서 파일이면 8003 문서 처리 서버로 전달
        return await _process_document_file(
            file=file,
            room_id=room_id,
            document_type=document_type,
        )

    except httpx.HTTPStatusError as e:
        return {
            "status": "error",
            "room_id": room_id,
            "document_id": None,
            "filename": filename,
            "type": document_type,
            "file_path": None,
            "json_path": None,
            "summary": None,
            "message": "외부 처리 서버 응답 오류가 발생했습니다.",
            "error": str(e),
        }

    except httpx.RequestError as e:
        return {
            "status": "error",
            "room_id": room_id,
            "document_id": None,
            "filename": filename,
            "type": document_type,
            "file_path": None,
            "json_path": None,
            "summary": None,
            "message": "외부 처리 서버에 연결할 수 없습니다.",
            "error": str(e),
        }

    except Exception as e:
        return {
            "status": "error",
            "room_id": room_id,
            "document_id": None,
            "filename": filename,
            "type": document_type,
            "file_path": None,
            "json_path": None,
            "summary": None,
            "message": "문서 업로드 또는 처리 중 오류가 발생했습니다.",
            "error": str(e),
        }