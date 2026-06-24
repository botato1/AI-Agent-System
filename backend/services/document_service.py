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
    get_tasks_by_document,
    delete_document,
    delete_document_chunks,
    update_chroma_status,
)
from backend.modules.rag.document_loader import load_document
from backend.modules.rag.chroma_client import delete_document as chroma_delete_document


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
        "chroma_status": None,
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


def _load_document_json(json_path: str) -> dict:
    """
    8000 로컬에 저장된 문서 처리 결과 JSON을 읽는다.
    """
    if not json_path:
        return {}

    try:
        path = Path(json_path)

        if not path.exists() or not path.is_file():
            return {}

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception as e:
        print(f"[document_service] 문서 JSON 읽기 실패: {json_path} / {repr(e)}")
        return {}


def _extract_original_text(document: dict, document_json: dict) -> str:
    """
    문서 원문 전체 텍스트를 추출한다.

    우선순위:
    1. documents.content_markdown
    2. JSON content_markdown
    3. JSON content
    4. JSON chunks[].text 또는 chunks[].content 합치기
    """
    content = (
        document.get("content_markdown")
        or document_json.get("content_markdown")
        or document_json.get("content")
        or ""
    )

    if content and content.strip():
        return content

    chunks = document_json.get("chunks") or []

    if isinstance(chunks, list):
        chunk_texts = []

        for chunk in chunks:
            if not isinstance(chunk, dict):
                continue

            text = chunk.get("content") or chunk.get("text") or ""

            if text and text.strip():
                chunk_texts.append(text.strip())

        return "\n\n".join(chunk_texts)

    return ""


def _extract_keywords(document_json: dict) -> list[str]:
    """
    문서 처리 결과 JSON에서 키워드를 추출한다.

    우선순위:
    1. keywords
    2. tags
    3. metadata.keywords
    4. metadata.tags

    없으면 빈 배열을 반환한다.
    """
    metadata = document_json.get("metadata") or {}

    keywords = (
        document_json.get("keywords")
        or document_json.get("tags")
        or metadata.get("keywords")
        or metadata.get("tags")
        or []
    )

    if isinstance(keywords, str):
        keyword = keywords.strip()
        return [keyword] if keyword else []

    if isinstance(keywords, list):
        return [
            str(keyword).strip()
            for keyword in keywords
            if str(keyword).strip()
        ]

    return []


def _extract_chunks(document_json: dict) -> list[dict]:
    """
    로컬 JSON의 chunks 배열을 프론트 상세 조회용 구조로 변환한다.
    """
    chunks = document_json.get("chunks") or []

    if not isinstance(chunks, list):
        return []

    result = []

    for idx, chunk in enumerate(chunks):
        if not isinstance(chunk, dict):
            continue

        content = chunk.get("content") or chunk.get("text") or ""

        if not str(content).strip():
            continue

        metadata = chunk.get("metadata") or {}

        for key in ["font", "size", "bbox", "confidence"]:
            if key in chunk and key not in metadata:
                metadata[key] = chunk.get(key)

        result.append({
            "chunk_index": chunk.get("chunk_index", idx),
            "page_number": chunk.get("page_number"),
            "content_type": (
                chunk.get("content_type")
                or chunk.get("type")
                or chunk.get("style")
                or "text"
            ),
            "content": str(content).strip(),
            "style": chunk.get("style"),
            "metadata": metadata,
        })

    return result


def _extract_content_types(chunks: list[dict]) -> list[str]:
    """
    chunks에서 content_type 목록을 중복 없이 추출한다.
    """
    content_types = []

    for chunk in chunks:
        content_type = chunk.get("content_type")

        if content_type and content_type not in content_types:
            content_types.append(content_type)

    return content_types


def _extract_analysis_metadata(document_json: dict) -> dict:
    """
    문서 처리 결과 JSON의 metadata에서 분석 관련 값을 추출한다.
    """
    metadata = document_json.get("metadata") or {}

    return {
        "page_count": (
            document_json.get("page_count")
            or metadata.get("page_count")
        ),
        "language": (
            document_json.get("language")
            or metadata.get("language")
        ),
        "confidence_score": (
            document_json.get("confidence_score")
            or metadata.get("confidence_score")
        ),
        "engines": (
            document_json.get("engines")
            or metadata.get("engines")
            or []
        ),
        "fallback_used": (
            document_json.get("fallback_used")
            if document_json.get("fallback_used") is not None
            else metadata.get("fallback_used")
        ),
    }


def _extract_organized_items(document_json: dict) -> dict:
    """
    문서 처리 결과 JSON에 정리된 항목이 있으면 추출한다.
    없으면 빈 배열로 반환한다.
    """
    return {
        "important_points": (
            document_json.get("important_points")
            or document_json.get("key_points")
            or document_json.get("main_points")
            or []
        ),
        "decisions": (
            document_json.get("decisions")
            or document_json.get("decision_items")
            or []
        ),
    }


def _make_fallback_summary(original_text: str, max_length: int = 500) -> str:
    if not original_text:
        return ""

    text = original_text.strip()

    if not text:
        return ""

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    if not lines:
        return text[:max_length]

    summary_text = " ".join(lines[:8])

    if len(summary_text) > max_length:
        return summary_text[:max_length].rstrip() + "..."

    return summary_text


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
            "chroma_status": None,
            "message": "8003 문서 처리 결과에 document_id가 없습니다.",
            "error": "document_id_missing",
        }

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
            "chroma_status": None,
            "message": "8003 문서 처리 결과에 content 또는 chunks가 없습니다.",
            "error": "document_content_missing",
        }

    processed_result["content_markdown"] = content_markdown

    # 5. 8003 응답 JSON 전체를 8000 서버 로컬에 저장
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
    try:
        chroma_load_result = load_document(
            document_id=saved_document_id,
            room_id=result_room_id,
        )

        if chroma_load_result.get("status") == "success":
            update_chroma_status(saved_document_id, "success")
            chroma_status = "success"
        else:
            update_chroma_status(saved_document_id, "failed")
            chroma_status = "failed"

        print(f"[document_service] ChromaDB 적재 결과: {chroma_load_result}")

    except Exception as e:
        update_chroma_status(saved_document_id, "failed")
        chroma_status = "failed"
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
        "chroma_status": chroma_status,
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
    - ChromaDB 적재 결과에 따라 chroma_status 업데이트
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


def get_document_detail(document_id: str) -> dict:
    try:
        # 1. 문서 기본 정보 조회
        document = get_document_by_id(document_id)

        if not document:
            return {
                "status": "error",
                "document_id": document_id,
                "document": None,
                "message": "문서를 찾을 수 없습니다.",
                "error": "document_not_found",
            }

        # 2. 8000 로컬 JSON 읽기
        json_path = document.get("json_path") or ""
        document_json = _load_document_json(json_path)

        # 3. raw 데이터 구성
        original_text = _extract_original_text(
            document=document,
            document_json=document_json,
        )

        chunks = _extract_chunks(document_json)

        # 4. analysis 데이터 구성
        keywords = _extract_keywords(document_json)
        analysis_metadata = _extract_analysis_metadata(document_json)
        content_types = _extract_content_types(chunks)

        summary = (
            document.get("summary")
            or document_json.get("summary")
            or _make_fallback_summary(original_text)
        )

        # 5. organized 데이터 구성
        tasks = get_tasks_by_document(document_id)
        organized_items = _extract_organized_items(document_json)

        # 6. 프론트 상세 조회 응답 구성
        return {
            "status": "success",
            "document_id": document_id,
            "document": {
                "document_id": document.get("id"),
                "room_id": document.get("conversation_id"),
                "filename": document.get("title"),
                "type": document.get("type"),
                "source": document.get("source"),
                "status": document.get("status"),
                "chroma_status": document.get("chroma_status"),
                "file_path": document.get("file_path"),
                "json_path": document.get("json_path"),
                "created_at": document.get("created_at"),

                "raw": {
                    "original_text": original_text,
                    "chunks": chunks,
                },

                "analysis": {
                    "summary": summary,
                    "keywords": keywords,
                    "page_count": analysis_metadata.get("page_count"),
                    "content_types": content_types,
                    "language": analysis_metadata.get("language"),
                    "confidence_score": analysis_metadata.get("confidence_score"),
                    "engines": analysis_metadata.get("engines"),
                    "fallback_used": analysis_metadata.get("fallback_used"),
                },

                "organized": {
                    "tasks": [
                        {
                            "task_id": task.get("id"),
                            "document_id": task.get("document_id"),
                            "room_id": task.get("conversation_id"),
                            "task": task.get("task"),
                            "assignee": task.get("assignee"),
                            "deadline": task.get("deadline"),
                            "status": task.get("status"),
                            "priority": task.get("priority"),
                            "created_at": task.get("created_at"),
                        }
                        for task in tasks
                    ],
                    "important_points": organized_items.get("important_points", []),
                    "decisions": organized_items.get("decisions", []),
                },
            },
            "message": "문서 상세 조회가 완료되었습니다.",
            "error": None,
        }

    except Exception as e:
        return {
            "status": "error",
            "document_id": document_id,
            "document": None,
            "message": "문서 상세 조회 중 오류가 발생했습니다.",
            "error": repr(e),
        }


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

        # 6. ChromaDB 벡터 삭제
        try:
            chroma_delete_document(document_id)
            chroma_deleted = True
            print(f"[document_service] ChromaDB 벡터 삭제 완료: {document_id}")
        except Exception as e:
            chroma_deleted = False
            print(f"[document_service] ChromaDB 벡터 삭제 실패: {repr(e)}")

        # 7. SQLite documents 삭제
        deleted_document = delete_document(document_id)

        # 8. 최종 상태 결정
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
                "chroma": chroma_deleted,
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