# 문서 업로드 및 처리 서비스
import os
import json
from pathlib import Path

from fastapi import UploadFile
import httpx

from backend.db.crud import (
    ensure_conversation,
    save_document_metadata,
    get_document_by_id,
    delete_document,
    delete_document_chunks,
)
from backend.modules.rag.document_loader import load_document


# 문서 처리 서버 8003
# 업로드: POST   /api/document
# 삭제:   DELETE /api/document/{document_id}
DOCUMENT_PROCESS_URL = os.getenv(
    "DOCUMENT_PROCESS_URL",
    "http://220.90.180.93:8003/api/document"
)


# 8003 문서 처리 서버에서 처리 가능한 문서 확장자
ALLOWED_DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".hwpx",
    ".png",
    ".jpg",
    ".jpeg",
}


def is_document_file(file: UploadFile) -> bool:
    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()

    return suffix in ALLOWED_DOCUMENT_EXTENSIONS


def _get_source(filename: str) -> str:
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        return "pdf"

    if suffix == ".hwpx":
        return "hwpx"

    if suffix in {".png", ".jpg", ".jpeg"}:
        return "image"

    return suffix.replace(".", "") or "file"


def _is_valid_document_type(document_type: str) -> bool:
    return document_type in {"document", "meeting"}


def _is_audio_file(file: UploadFile) -> bool:
    """
    음성 파일이 /api/documents/upload로 잘못 들어온 경우를 구분하기 위한 함수.
    실제 STT 처리는 /api/stt/upload에서 담당한다.
    """
    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()

    if suffix in {".mp3", ".wav", ".m4a", ".webm"}:
        return True

    if file.content_type and file.content_type.startswith("audio/"):
        return True

    return False


def _build_error_response(
    room_id: str,
    filename: str,
    document_type: str,
    message: str,
    error: str,
) -> dict:
    return {
        "status": "error",
        "room_id": room_id,
        "document_id": None,
        "filename": filename,
        "type": document_type,
        "file_path": None,
        "json_path": None,
        "summary": None,
        "chroma_load_result": None,
        "message": message,
        "error": error,
    }


def _safe_delete_local_file(file_path: str) -> bool:
    """
    8000 서버에서 접근 가능한 로컬 파일이면 삭제한다.

    8003 서버의 Windows 경로처럼 현재 서버에서 접근할 수 없는 경로는
    exists()가 False가 되므로 삭제하지 않고 False를 반환한다.
    """
    if not file_path:
        return False

    try:
        path = Path(file_path)

        if path.exists() and path.is_file():
            path.unlink()
            return True

    except Exception as e:
        print(f"[document_service] 로컬 파일 삭제 실패: {file_path} / {repr(e)}")

    return False

# 8003 문서 처리 서버에 원본 문서 파일 및 처리 결과 JSON 삭제를 요청
def _delete_document_from_8003(document_id: str) -> dict:
    delete_url = f"{DOCUMENT_PROCESS_URL.rstrip('/')}/{document_id}"

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.delete(delete_url)

        try:
            response_data = response.json()
        except Exception:
            response_data = {
                "status": "error",
                "message": "8003 삭제 응답을 JSON으로 파싱할 수 없습니다.",
                "document_id": document_id,
                "deleted": {
                    "file": False,
                    "json": False,
                },
                "error": response.text,
            }

        return {
            "called": True,
            "url": delete_url,
            "status_code": response.status_code,
            "status": response_data.get("status"),
            "message": response_data.get("message"),
            "document_id": response_data.get("document_id") or document_id,
            "deleted": response_data.get("deleted") or {
                "file": False,
                "json": False,
            },
            "error": response_data.get("error"),
        }

    except httpx.RequestError as e:
        return {
            "called": False,
            "url": delete_url,
            "status_code": None,
            "status": "error",
            "message": "8003 문서 삭제 서버에 연결할 수 없습니다.",
            "document_id": document_id,
            "deleted": {
                "file": False,
                "json": False,
            },
            "error": repr(e),
        }

    except Exception as e:
        return {
            "called": False,
            "url": delete_url,
            "status_code": None,
            "status": "error",
            "message": "8003 문서 삭제 요청 중 오류가 발생했습니다.",
            "document_id": document_id,
            "deleted": {
                "file": False,
                "json": False,
            },
            "error": repr(e),
        }


def _save_processed_result_to_local_json(
    processed_result: dict,
    document_id: str,
) -> str:
    """
    8003이 내려준 json_path는 8003 서버의 로컬 경로일 수 있다.
    8000 서버가 Mac이나 다른 환경에서 실행되면 위 경로를 직접 읽을 수 없다.
    그래서 8003 응답 JSON 전체를 8000 서버 로컬에 다시 저장하고,
    그 로컬 json_path를 SQLite documents.json_path에 저장한다.
    """
    local_json_dir = Path("data/uploads/documents")
    local_json_dir.mkdir(parents=True, exist_ok=True)

    local_json_path = local_json_dir / f"{document_id}.json"

    # 8003 원본 json_path는 참고용으로 보존
    original_json_path = processed_result.get("json_path") or ""
    processed_result["original_json_path"] = original_json_path

    # document_loader가 읽을 수 있는 8000 로컬 경로로 교체
    processed_result["json_path"] = str(local_json_path)

    with open(local_json_path, "w", encoding="utf-8") as f:
        json.dump(processed_result, f, ensure_ascii=False, indent=2)

    return str(local_json_path)


# 문서 파일 처리
# 프론트에서 받은 문서 파일을 8003 문서 처리 서버로 전달하고,
# 8003 처리 결과를 documents 테이블에 저장한 뒤 ChromaDB에 적재한다.
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
    document_id = processed_result.get("document_id") or processed_result.get("id")
    result_room_id = processed_result.get("room_id") or room_id
    result_filename = (
        processed_result.get("filename")
        or processed_result.get("title")
        or filename
    )
    result_type = processed_result.get("type") or document_type

    file_path = processed_result.get("file_path") or ""
    summary = processed_result.get("summary") or ""

    # 8003 응답에서는 content_markdown이 비어 있고 content에 전체 텍스트가 들어올 수 있음
    content_markdown = (
        processed_result.get("content_markdown")
        or processed_result.get("content")
        or ""
    )

    chunks = processed_result.get("chunks") or []

    # 4. 필수값 검증
    if not document_id:
        return {
            "status": "error",
            "room_id": result_room_id,
            "document_id": None,
            "filename": result_filename,
            "type": result_type,
            "file_path": file_path,
            "json_path": processed_result.get("json_path") or "",
            "summary": summary,
            "chroma_load_result": None,
            "message": "8003 문서 처리 결과에 document_id가 없습니다.",
            "error": "document_id_missing",
        }

    # content_markdown이 없더라도 chunks[]가 있으면 ChromaDB 적재는 가능하므로 통과
    has_content = bool(content_markdown.strip())
    has_chunks = isinstance(chunks, list) and len(chunks) > 0

    if not has_content and not has_chunks:
        return {
            "status": "error",
            "room_id": result_room_id,
            "document_id": document_id,
            "filename": result_filename,
            "type": result_type,
            "file_path": file_path,
            "json_path": processed_result.get("json_path") or "",
            "summary": summary,
            "chroma_load_result": None,
            "message": "8003 문서 처리 결과에 content 또는 chunks가 없습니다.",
            "error": "document_content_missing",
        }

    # document_loader 또는 추후 조회에서 content_markdown으로도 접근할 수 있게 정리
    processed_result["content_markdown"] = content_markdown

    # 5. 8003 응답 JSON 전체를 8000 서버 로컬에 저장
    #    SQLite에는 8003 서버의 Windows json_path가 아니라 8000 로컬 json_path를 저장한다.
    json_path = _save_processed_result_to_local_json(
        processed_result=processed_result,
        document_id=document_id,
    )

    # 6. 채팅방 생성 또는 갱신
    ensure_conversation(
        conversation_id=result_room_id,
        title=result_filename,
    )

    # 7. documents 테이블에 문서 메타데이터 저장
    saved_document_id = save_document_metadata({
        "id": document_id,
        "conversation_id": result_room_id,
        "title": result_filename,
        "type": result_type,
        "source": _get_source(result_filename),
        "file_path": file_path,
        "json_path": json_path,
        "content_markdown": content_markdown,
        "summary": summary,
        "status": "processed",
        "notion_url": "",
        "error": "",
    })

    # 8. SQLite 저장 완료 후 ChromaDB 적재
    # document_loader는 documents.json_path를 다시 읽어서
    # chunks[] / transcription[] 기반으로 ChromaDB에 저장한다.
    try:
        chroma_load_result = load_document(
            document_id=saved_document_id,
            room_id=result_room_id,
        )
        print(f"[document_service] ChromaDB 적재 결과: {chroma_load_result}")

    except Exception as e:
        chroma_load_result = {
            "status": "error",
            "chunk_count": 0,
            "document_id": saved_document_id,
            "error": repr(e),
        }
        print(f"[document_service] ChromaDB 적재 실패: {repr(e)}")

    # 9. 프론트에 최종 응답 반환
    return {
        "status": "success",
        "room_id": result_room_id,
        "document_id": saved_document_id,
        "filename": result_filename,
        "type": result_type,
        "file_path": file_path,
        "json_path": json_path,
        "summary": summary,
        "chroma_load_result": chroma_load_result,
        "message": "문서 처리, 메타데이터 저장 및 ChromaDB 적재 요청이 완료되었습니다.",
        "error": None,
    }


async def upload_and_process_document(
    file: UploadFile,
    room_id: str,
    document_type: str = "document",
) -> dict:
    """
    문서 업로드 처리 함수.
    - 8003 문서 처리 서버로 전달
    - 처리 결과를 받아 documents 테이블 저장
    - 저장 완료 후 document_loader.load_document()로 ChromaDB 적재
    """
    filename = Path(file.filename).name if file and file.filename else "uploaded_file"

    try:
        # 1. 음성 파일이 문서 업로드 API로 들어온 경우 차단
        if _is_audio_file(file):
            return _build_error_response(
                room_id=room_id,
                filename=filename,
                document_type="voice",
                message="음성 파일은 /api/stt/upload API를 사용해 주세요.",
                error="use_stt_upload_api",
            )

        # 2. 문서 유형 검사
        if not _is_valid_document_type(document_type):
            return _build_error_response(
                room_id=room_id,
                filename=filename,
                document_type=document_type,
                message="지원하지 않는 문서 유형입니다.",
                error="unsupported_document_type",
            )

        # 3. 문서 파일 확장자 검사
        if not is_document_file(file):
            return _build_error_response(
                room_id=room_id,
                filename=filename,
                document_type=document_type,
                message="지원하지 않는 파일 형식입니다.",
                error="unsupported_file_type",
            )

        # 4. 문서 파일이면 8003 문서 처리 서버로 전달
        return await _process_document_file(
            file=file,
            room_id=room_id,
            document_type=document_type,
        )

    except httpx.HTTPStatusError as e:
        return _build_error_response(
            room_id=room_id,
            filename=filename,
            document_type=document_type,
            message="외부 처리 서버 응답 오류가 발생했습니다.",
            error=repr(e),
        )

    except httpx.RequestError as e:
        return _build_error_response(
            room_id=room_id,
            filename=filename,
            document_type=document_type,
            message="외부 처리 서버에 연결할 수 없습니다.",
            error=repr(e),
        )

    except Exception as e:
        return _build_error_response(
            room_id=room_id,
            filename=filename,
            document_type=document_type,
            message="문서 업로드 또는 처리 중 오류가 발생했습니다.",
            error=repr(e),
        )

# 문서 삭제 처리 함수
# ChromaDB 삭제는 chroma_client에 삭제 함수가 준비되면 추가 연결
def delete_processed_document(document_id: str) -> dict:
    try:
        # 1. 삭제 대상 문서 조회
        document = get_document_by_id(document_id)

        if not document:
            return {
                "status": "error",
                "document_id": document_id,
                "message": "삭제할 문서를 찾을 수 없습니다.",
                "deleted": {
                    "document_chunks": 0,
                    "document": False,
                    "local_json_file": False,
                    "local_source_file": False,
                    "external_file": False,
                    "external_json": False,
                    "chroma": False,
                },
                "document_server_result": None,
                "error": "document_not_found",
            }

        json_path = document.get("json_path") or ""
        file_path = document.get("file_path") or ""

        # 2. 8003 서버 원본 문서 및 처리 JSON 삭제 요청
        document_server_result = _delete_document_from_8003(document_id)

        external_deleted = document_server_result.get("deleted") or {}
        external_file_deleted = bool(external_deleted.get("file"))
        external_json_deleted = bool(external_deleted.get("json"))

        # 3. SQLite document_chunks 삭제
        deleted_chunks_count = delete_document_chunks(document_id)

        # 4. 8000 로컬 JSON 파일 삭제
        deleted_local_json_file = _safe_delete_local_file(json_path)

        # 5. 8000에서 접근 가능한 원본 파일이면 삭제
        deleted_local_source_file = _safe_delete_local_file(file_path)

        # 6. SQLite documents 삭제
        deleted_document = delete_document(document_id)

        # 7. 최종 상태 결정
        # 8000 내부 삭제는 성공했지만 8003 삭제가 실패할 수 있으므로 상태를 분리한다.
        if document_server_result.get("status") == "success":
            final_status = "success"
            message = "문서 삭제가 완료되었습니다."
            error = None

        elif document_server_result.get("status") == "partial_success":
            final_status = "partial_success"
            message = "8000 문서는 삭제되었지만, 8003 서버에서 일부 파일만 삭제되었습니다."
            error = document_server_result.get("error")

        else:
            final_status = "partial_success"
            message = "8000 문서는 삭제되었지만, 8003 서버 원본 삭제는 실패했습니다."
            error = document_server_result.get("error")

        return {
            "status": final_status,
            "document_id": document_id,
            "message": message,
            "deleted": {
                "document_chunks": deleted_chunks_count,
                "document": deleted_document,
                "local_json_file": deleted_local_json_file,
                "local_source_file": deleted_local_source_file,
                "external_file": external_file_deleted,
                "external_json": external_json_deleted,
                "chroma": False,
            },
            "document_server_result": document_server_result,
            "error": error,
        }

    except Exception as e:
        return {
            "status": "error",
            "document_id": document_id,
            "message": "문서 삭제 중 오류가 발생했습니다.",
            "deleted": None,
            "document_server_result": None,
            "error": repr(e),
        }