# backend/services/stt_upload_service.py
# STT 업로드 및 DB 저장 서비스
import json
import os
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import UploadFile

from backend.db.crud import (
    ensure_conversation,
    save_document_metadata,
    save_document_chunks,
    delete_document_chunks,
    get_document_by_id,
    get_document_chunks,
    get_all_voice_documents,
    delete_document,
    update_chroma_status,
)
from backend.modules.rag.document_loader import (
    _load_voice,
    _get_upload_context,
    _build_base_meta,
)
from backend.modules.rag.chroma_client import delete_document as chroma_delete_document


# room_id 없이 업로드된 음성을 documents.conversation_id에 저장할 내부 값
# conversations 테이블에는 생성하지 않음
VOICE_LIBRARY_ROOM_ID = "__voice_library__"


# 8001 STT 서버 URL
STT_BASE_URL = os.getenv(
    "STT_BASE_URL",
    "http://192.168.0.2:8001"
)

STT_PROCESS_URL = os.getenv(
    "STT_PROCESS_URL",
    f"{STT_BASE_URL}/api/stt"
)


# 허용할 음성 확장자
ALLOWED_STT_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".m4a",
    ".webm",
}


def is_allowed_stt_file(file: UploadFile) -> bool:
    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()

    if suffix in ALLOWED_STT_EXTENSIONS:
        return True

    if file.content_type and file.content_type.startswith("audio/"):
        return True

    return False


def _format_time(value) -> str:
    """
    초 단위 시간을 문자열로 변환한다.
    값이 없으면 ?로 표시한다.
    """
    if value is None:
        return "?"

    try:
        return f"{float(value):.2f}s"
    except Exception:
        return str(value)


def _safe_json_loads(value) -> dict:
    """
    documents.metadata에 저장된 JSON 문자열을 dict로 변환한다.
    """
    if not value:
        return {}

    if isinstance(value, dict):
        return value

    try:
        return json.loads(value)
    except Exception:
        return {}


def _build_stt_content_markdown(data: dict) -> str:
    """
    STT 결과의 content와 transcription을 기반으로
    LLM/RAG에서 사용할 content_markdown을 만든다.
    """
    metadata = data.get("metadata") or {}

    title = (
        metadata.get("original_filename")
        or data.get("title")
        or "STT 결과"
    )

    content = data.get("content") or ""
    transcription = data.get("transcription") or []

    lines = [
        f"# {title}",
        "",
        "## 전체 전사 내용",
        "",
        content.strip() if content else "",
        "",
        "## 화자별 전사",
        "",
    ]

    if transcription:
        for item in transcription:
            start = _format_time(item.get("start"))
            end = _format_time(item.get("end"))
            speaker = item.get("speaker") or "UNKNOWN"
            text = item.get("text") or ""

            if not text.strip():
                continue

            lines.append(f"- [{start} ~ {end}] {speaker}: {text.strip()}")
    else:
        lines.append("- 전사 상세 정보가 없습니다.")

    return "\n".join(lines).strip()


def _get_stt_filename(data: dict, fallback_filename: str) -> str:
    metadata = data.get("metadata") or {}

    return (
        metadata.get("original_filename")
        or data.get("filename")
        or data.get("title")
        or fallback_filename
    )


def _get_stt_file_path(data: dict) -> str:
    metadata = data.get("metadata") or {}

    return (
        metadata.get("original_file_url")
        or data.get("file_path")
        or ""
    )


def _get_duration_sec(metadata: dict) -> float | None:
    """
    STT metadata에서 duration 값을 가져온다.
    STT 서버 응답 키가 duration_sec 또는 duration 등으로 올 수 있어서 안전하게 처리한다.
    """
    if not metadata:
        return None

    duration = (
        metadata.get("duration_sec")
        or metadata.get("duration")
        or metadata.get("total_duration_sec")
    )

    if duration is None:
        return None

    try:
        return float(duration)
    except Exception:
        return None


def _load_stt_json(json_path: str) -> dict:
    """
    8000 로컬에 저장된 STT 결과 JSON을 읽는다.
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
        print(f"[stt_upload_service] STT JSON 읽기 실패: {json_path} / {repr(e)}")
        return {}


def _save_stt_result_to_local_json(
    document_id: str,
    content_markdown: str,
    transcription: list,
    metadata: dict,
    title: str,
    summary: str,
) -> str:
    """
    STT 결과를 8000 서버 로컬 JSON 파일로 저장한다.
    서버 이관 후 NAS 경로로 변경 예정.
    """
    local_json_dir = Path("data/uploads/voice")
    local_json_dir.mkdir(parents=True, exist_ok=True)

    local_json_path = local_json_dir / f"{document_id}.json"

    stt_json = {
        "id": document_id,
        "title": title,
        "type": "voice",
        "source": "voice",
        "content": content_markdown,
        "content_markdown": content_markdown,
        "transcription": transcription,
        "metadata": metadata,
        "summary": summary,
    }

    with open(local_json_path, "w", encoding="utf-8") as f:
        json.dump(stt_json, f, ensure_ascii=False, indent=2)

    return str(local_json_path)


def _extract_plain_content_from_json(stt_json: dict) -> str:
    """
    로컬 JSON에서 전체 전사 텍스트를 추출한다.
    """
    content_markdown = stt_json.get("content_markdown") or stt_json.get("content") or ""

    if not content_markdown:
        return ""

    marker = "## 전체 전사 내용"
    next_marker = "## 화자별 전사"

    if marker not in content_markdown:
        return content_markdown.strip()

    content_part = content_markdown.split(marker, 1)[1]

    if next_marker in content_part:
        content_part = content_part.split(next_marker, 1)[0]

    return content_part.strip()


def _chunks_to_transcription(chunks: list[dict]) -> list[dict]:
    """
    document_chunks 조회 결과를 프론트가 쓰는 transcription 형식으로 변환한다.
    """
    transcription = []

    for chunk in chunks:
        transcription.append({
            "chunk_id": chunk.get("id"),
            "chunk_index": chunk.get("chunk_index"),
            "start": chunk.get("start_time"),
            "end": chunk.get("end_time"),
            "speaker": chunk.get("speaker"),
            "text": chunk.get("content") or "",
            "user_edited": bool(chunk.get("user_edited")),
        })

    return transcription


def _extract_file_id_from_original_file_url(original_file_url: str | None) -> str | None:
    """
    8001 삭제 API에서 사용하는 file_id를 original_file_url에서 추출한다.
    """
    if not original_file_url:
        return None

    try:
        parsed = urlparse(original_file_url)
        filename = Path(parsed.path).name

        if not filename:
            return None

        return Path(filename).stem

    except Exception:
        return None


def _resolve_stt_file_id(document_id: str, metadata: dict) -> str:
    """
    8001 DELETE /api/stt/{file_id} 호출에 사용할 file_id를 결정한다.

    우선순위:
    1. metadata.original_file_url에서 추출한 audio_xxx
    2. metadata.file_id
    3. document_id
    """
    metadata = metadata or {}

    original_file_url = metadata.get("original_file_url")
    file_id_from_url = _extract_file_id_from_original_file_url(original_file_url)

    return (
        file_id_from_url
        or metadata.get("file_id")
        or document_id
    )


def _is_voice_library_room_id(conversation_id: str | None) -> bool:
    """
    room_id 없이 업로드된 독립 음성인지 확인한다.
    """
    return conversation_id == VOICE_LIBRARY_ROOM_ID


def _build_success_response(
    room_id: str | None,
    document_id: str,
    filename: str,
    title: str,
    file_path: str,
    summary: str,
    saved_chunk_count: int,
    transcription: list,
    metadata: dict,
    chroma_status: str,
) -> dict:
    duration_sec = _get_duration_sec(metadata)
    file_id = _resolve_stt_file_id(document_id, metadata)

    return {
        "status": "success",
        "room_id": room_id,
        "document_id": document_id,
        "file_id": file_id,
        "filename": filename,
        "title": title,
        "type": "voice",
        "source": "voice",
        "file_path": file_path,
        "summary": summary,
        "chunk_count": saved_chunk_count,
        "chroma_status": chroma_status,

        # 프론트 분석 결과 페이지 즉시 이동용 필드
        "duration_sec": duration_sec,
        "transcription": transcription,
        "metadata": metadata,

        "message": "STT 처리 및 메타데이터 저장이 완료되었습니다.",
        "error": None,
    }


def _build_error_response(
    room_id: str | None,
    filename: str,
    message: str,
    error: str,
) -> dict:
    return {
        "status": "error",
        "room_id": room_id,
        "document_id": None,
        "file_id": None,
        "filename": filename,
        "title": None,
        "type": "voice",
        "source": "voice",
        "file_path": None,
        "summary": None,
        "chunk_count": 0,
        "chroma_status": None,
        "duration_sec": None,
        "transcription": [],
        "metadata": None,
        "message": message,
        "error": error,
    }


async def upload_and_process_stt(
    file: UploadFile,
    room_id: str | None = None,
) -> dict:
    """
    STT 업로드 통합 처리 함수.

    흐름:
    1. 프론트에서 받은 음성 파일 검증
    2. 8001 STT 서버로 파일 전달
    3. 8001 응답 data 파싱
    4. STT 결과 로컬 JSON 저장 (서버 이관 후 NAS 경로로 변경 예정)
    5. documents 테이블 저장
    6. document_chunks 테이블 저장
    7. ChromaDB 적재 및 chroma_status 업데이트
    8. 프론트에 document_id, file_id, transcription, metadata, chroma_status 반환
    """
    filename = Path(file.filename).name if file and file.filename else "uploaded_audio"

    db_room_id = room_id or VOICE_LIBRARY_ROOM_ID

    try:
        # 1. 파일 형식 검증
        if not is_allowed_stt_file(file):
            return _build_error_response(
                room_id=room_id,
                filename=filename,
                message="지원하지 않는 음성 파일 형식입니다.",
                error="unsupported_stt_file_type",
            )

        # 2. 파일 읽기
        file_content = await file.read()

        # 3. 8001 STT 서버 호출
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                STT_PROCESS_URL,
                files={
                    "file": (
                        filename,
                        file_content,
                        file.content_type or "application/octet-stream",
                    )
                },
                data={
                    "topic": "",
                },
            )

        response.raise_for_status()
        stt_result = response.json()

        # 4. STT 응답 상태 확인
        if stt_result.get("status") != "success":
            return _build_error_response(
                room_id=room_id,
                filename=filename,
                message=stt_result.get("message") or "STT 처리에 실패했습니다.",
                error=str(stt_result.get("error") or "stt_process_failed"),
            )

        data = stt_result.get("data") or {}

        if not data:
            return _build_error_response(
                room_id=room_id,
                filename=filename,
                message="STT 서버 응답에 data가 없습니다.",
                error="stt_data_missing",
            )

        # 5. 저장에 필요한 값 추출
        document_id = data.get("id")
        title = data.get("title") or filename
        result_filename = _get_stt_filename(data, filename)
        file_path = _get_stt_file_path(data)
        summary = data.get("summary") or ""
        status = data.get("status") or "processed"
        error = data.get("error") or ""

        transcription = data.get("transcription") or []
        metadata = data.get("metadata") or {}

        if data.get("language") and not metadata.get("language"):
            metadata["language"] = data.get("language")

        content_markdown = _build_stt_content_markdown(data)

        # 6. 필수값 검증
        if not document_id:
            return _build_error_response(
                room_id=room_id,
                filename=result_filename,
                message="STT 결과에 document_id로 사용할 id가 없습니다.",
                error="stt_document_id_missing",
            )

        # 7. 채팅방 생성 또는 갱신
        if room_id:
            ensure_conversation(
                conversation_id=room_id,
                title=result_filename,
            )

        # 8. STT 결과 로컬 JSON 저장
        stt_json_path = _save_stt_result_to_local_json(
            document_id=document_id,
            content_markdown=content_markdown,
            transcription=transcription,
            metadata=metadata,
            title=result_filename or title,
            summary=summary,
        )

        # 9. documents 테이블 저장
        saved_document_id = save_document_metadata({
            "id": document_id,
            "conversation_id": db_room_id,
            "title": result_filename or title,
            "type": "voice",
            "source": "voice",
            "file_path": file_path,
            "json_path": stt_json_path,
            "summary": summary,
            "status": status,
            "notion_url": data.get("notion_url") or "",
            "error": error,
            "metadata": json.dumps(metadata, ensure_ascii=False),
        })

        # 10. document_chunks 테이블 저장
        delete_document_chunks(saved_document_id)

        saved_chunk_count = save_document_chunks(
            document_id=saved_document_id,
            transcription=transcription,
        )

        # 11. ChromaDB 적재
        try:
            doc_for_chroma = {
                "id": saved_document_id,
                "document_id": saved_document_id,
                "title": result_filename or title,
                "filename": result_filename or title,
                "type": "voice",
                "source": "voice",
                "transcription": transcription,
                "language": metadata.get("language", "ko"),
                "created_at": "",
                "status": "processed",
                "notion_url": "",
                "error": "",
                "tags": [],
                "importance_score": 0,
            }

            upload_context = _get_upload_context("voice")
            base_meta = _build_base_meta(doc_for_chroma, db_room_id)
            base_meta["document_id"] = saved_document_id

            chroma_load_result = _load_voice(doc_for_chroma, base_meta, upload_context)

            if chroma_load_result.get("status") == "success":
                update_chroma_status(saved_document_id, "success")
                chroma_status = "success"
            else:
                update_chroma_status(saved_document_id, "failed")
                chroma_status = "failed"

            print(f"[stt_upload_service] ChromaDB 적재 결과: {chroma_load_result}")

        except Exception as e:
            update_chroma_status(saved_document_id, "failed")
            chroma_status = "failed"
            print(f"[stt_upload_service] ChromaDB 적재 실패: {repr(e)}")

        # 12. 프론트 응답 반환
        return _build_success_response(
            room_id=room_id,
            document_id=saved_document_id,
            filename=result_filename,
            title=title,
            file_path=file_path,
            summary=summary,
            saved_chunk_count=saved_chunk_count,
            transcription=transcription,
            metadata=metadata,
            chroma_status=chroma_status,
        )

    except httpx.HTTPStatusError as e:
        return _build_error_response(
            room_id=room_id,
            filename=filename,
            message="STT 서버 응답 오류가 발생했습니다.",
            error=str(e),
        )

    except httpx.RequestError as e:
        return _build_error_response(
            room_id=room_id,
            filename=filename,
            message="STT 서버에 연결할 수 없습니다.",
            error=str(e),
        )

    except Exception as e:
        return _build_error_response(
            room_id=room_id,
            filename=filename,
            message="STT 업로드 또는 처리 중 오류가 발생했습니다.",
            error=str(e),
        )


def get_stt_list() -> dict:
    """
    업로드된 모든 음성 파일 목록 조회.
    8001 서버를 다시 호출하지 않고 8000 DB의 documents 기준으로 조회한다.
    """
    try:
        rows = get_all_voice_documents()

        data = []

        for row in rows:
            metadata = _safe_json_loads(row.get("metadata"))
            duration_sec = _get_duration_sec(metadata)
            file_id = _resolve_stt_file_id(row.get("id"), metadata)

            conversation_id = row.get("conversation_id")
            room_id = None if _is_voice_library_room_id(conversation_id) else conversation_id

            data.append({
                "document_id": row.get("id"),
                "file_id": file_id,
                "room_id": room_id,
                "filename": row.get("title"),
                "title": row.get("title"),
                "type": row.get("type"),
                "source": row.get("source"),
                "summary": row.get("summary") or "",
                "status": row.get("status"),
                "chroma_status": row.get("chroma_status"),
                "file_path": row.get("file_path"),
                "duration_sec": duration_sec,
                "metadata": metadata,
                "created_at": row.get("created_at"),
            })

        return {
            "status": "success",
            "data": data,
            "message": "음성 목록 조회가 완료되었습니다.",
            "error": None,
        }

    except Exception as e:
        return {
            "status": "error",
            "data": [],
            "message": "음성 목록 조회 중 오류가 발생했습니다.",
            "error": str(e),
        }


def get_stt_detail(document_id: str) -> dict:
    """
    특정 음성 파일의 상세 정보와 발화 단위 전사 결과를 조회한다.
    8000 DB의 documents, document_chunks, 로컬 JSON 기준으로 조회한다.
    """
    try:
        document = get_document_by_id(document_id)

        if not document:
            return {
                "status": "error",
                "data": None,
                "message": "음성 파일 정보를 찾을 수 없습니다.",
                "error": "stt_document_not_found",
            }

        if document.get("type") != "voice":
            return {
                "status": "error",
                "data": None,
                "message": "요청한 문서는 음성 파일이 아닙니다.",
                "error": "not_voice_document",
            }

        chunks = get_document_chunks(document_id)
        transcription = _chunks_to_transcription(chunks)

        metadata = _safe_json_loads(document.get("metadata"))
        file_id = _resolve_stt_file_id(document_id, metadata)

        # 로컬 JSON에서 content_markdown 읽기
        json_path = document.get("json_path") or ""
        stt_json = _load_stt_json(json_path)
        content_markdown = stt_json.get("content_markdown") or ""
        content = _extract_plain_content_from_json(stt_json)

        conversation_id = document.get("conversation_id")
        room_id = None if _is_voice_library_room_id(conversation_id) else conversation_id

        data = {
            "id": document.get("id"),
            "document_id": document.get("id"),
            "file_id": file_id,
            "room_id": room_id,
            "title": document.get("title"),
            "filename": document.get("title"),
            "type": document.get("type"),
            "source": document.get("source"),
            "content": content,
            "content_markdown": content_markdown,
            "summary": document.get("summary") or "",
            "language": metadata.get("language") or "ko",
            "created_at": document.get("created_at"),
            "tags": metadata.get("tags") or ["voice_upload"],
            "status": document.get("status"),
            "chroma_status": document.get("chroma_status"),
            "notion_url": document.get("notion_url"),
            "chroma_id": metadata.get("chroma_id"),
            "error": document.get("error"),
            "user_edited": metadata.get("user_edited", False),
            "transcription": transcription,
            "metadata": metadata,
        }

        return {
            "status": "success",
            "data": data,
            "message": "음성 상세 조회가 완료되었습니다.",
            "error": None,
        }

    except Exception as e:
        return {
            "status": "error",
            "data": None,
            "message": "음성 상세 조회 중 오류가 발생했습니다.",
            "error": str(e),
        }


async def delete_stt_document(document_id: str) -> dict:
    """
    특정 음성 파일을 삭제한다.

    흐름:
    1. 8000 DB에서 documents 조회
    2. metadata.original_file_url에서 8001 file_id 추출
    3. 8001 DELETE /api/stt/{file_id} 호출
    4. ChromaDB 벡터 삭제
    5. 8000 로컬 JSON 파일 삭제
    6. 8000 DB에서 document_chunks 삭제
    7. 8000 DB에서 documents 삭제
    """
    try:
        document = get_document_by_id(document_id)

        if not document:
            return {
                "status": "error",
                "document_id": document_id,
                "file_id": None,
                "message": "음성 파일 정보를 찾을 수 없습니다.",
                "error": "stt_document_not_found",
            }

        if document.get("type") != "voice":
            return {
                "status": "error",
                "document_id": document_id,
                "file_id": None,
                "message": "요청한 문서는 음성 파일이 아닙니다.",
                "error": "not_voice_document",
            }

        metadata = _safe_json_loads(document.get("metadata"))
        file_id = _resolve_stt_file_id(document_id, metadata)
        json_path = document.get("json_path") or ""

        stt_delete_url = f"{STT_BASE_URL}/api/stt/{file_id}"

        stt_delete_error = None

        # 1. 8001 서버 원본 음성/json 삭제 요청
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.delete(stt_delete_url)

            if response.status_code >= 400:
                stt_delete_error = response.text

        except Exception as e:
            stt_delete_error = str(e)

        # 2. ChromaDB 벡터 삭제
        try:
            chroma_delete_document(document_id)
            print(f"[stt_upload_service] ChromaDB 벡터 삭제 완료: {document_id}")
        except Exception as e:
            print(f"[stt_upload_service] ChromaDB 벡터 삭제 실패: {repr(e)}")

        # 3. 로컬 JSON 파일 삭제
        if json_path:
            try:
                local_path = Path(json_path)
                if local_path.exists() and local_path.is_file():
                    local_path.unlink()
                    print(f"[stt_upload_service] 로컬 JSON 삭제 완료: {json_path}")
            except Exception as e:
                print(f"[stt_upload_service] 로컬 JSON 삭제 실패: {repr(e)}")

        # 4. 8000 DB 삭제
        delete_document_chunks(document_id)
        db_deleted = delete_document(document_id)

        if stt_delete_error:
            return {
                "status": "partial_success",
                "document_id": document_id,
                "file_id": file_id,
                "message": "8000 DB 데이터는 삭제되었지만, 8001 원본 파일 삭제에 실패했습니다.",
                "error": stt_delete_error,
            }

        if not db_deleted:
            return {
                "status": "error",
                "document_id": document_id,
                "file_id": file_id,
                "message": "8000 DB 문서 삭제에 실패했습니다.",
                "error": "db_delete_failed",
            }

        return {
            "status": "success",
            "document_id": document_id,
            "file_id": file_id,
            "message": "음성 파일 및 STT 분석 결과가 삭제되었습니다.",
            "error": None,
        }

    except Exception as e:
        return {
            "status": "error",
            "document_id": document_id,
            "file_id": None,
            "message": "음성 삭제 중 오류가 발생했습니다.",
            "error": str(e),
        }