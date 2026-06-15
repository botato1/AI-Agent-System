# 문서 업로드 및 처리 서비스
from pathlib import Path
from uuid import uuid4
from fastapi import UploadFile

from backend.modules.rag.document_loader import load_and_insert
from backend.db.crud import ensure_conversation, save_document_metadata


# TODO: 문서/음성 처리 담당자와 최종 지원 확장자 확정 필요
# 현재는 테스트 및 임시 연동을 위한 허용 목록
ALLOWED_DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".png", ".jpg", ".jpeg",
}

# 프로젝트 루트 기준 data/raw 경로
BASE_DIR = Path(__file__).resolve().parents[2]
UPLOAD_DIR = BASE_DIR / "data" / "raw"


# 업로드 가능한 문서 파일인지 확장자로 검사하는 함수
def is_allowed_document_file(file: UploadFile) -> bool:
    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()

    # 1. 문서/이미지 파일은 확장자로 검사
    if suffix in ALLOWED_DOCUMENT_EXTENSIONS:
        return True

    # 2. 음성 파일은 MIME 타입으로 검사
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
        # 0. document_id를 먼저 생성
        # 이 id를 SQLite documents 테이블과 ChromaDB metadata에 동일하게 사용해야 함
        document_id = str(uuid4())

        filename = Path(file.filename).name if file.filename else f"{document_id}.file"

        # 1. 파일 형식 검사
        if not is_allowed_document_file(file):
            return {
                "status": "error",
                "room_id": room_id,
                "document_id": None,
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

        # 6. 파일 형식 정보 생성
        suffix = Path(filename).suffix.lower()
        document_type = _get_document_type(filename, file.content_type)
        source = _get_source(filename, file.content_type)

        # 7. 업로드만 해도 채팅방 목록에 나오도록 conversations 생성/갱신
        ensure_conversation(room_id, filename)

        # 8. documents 테이블에 먼저 저장
        # save_document_metadata가 반환한 id를 최종 document_id로 사용
        saved_document_id = save_document_metadata({
            "id": document_id,
            "conversation_id": room_id,
            "title": filename,
            "type": document_type,
            "source": source,
            "file_path": str(save_path),
            "summary": "",
            "status": "processed",
            "notion_url": "",
            "error": "",
        })

        # 9. 파일 형식에 따라 처리 분기
        if suffix == ".pdf":
            # 핵심:
            # ChromaDB에 넣을 때 SQLite documents 테이블에 저장된 id와 같은 값을 넘김
            inserted_document_id = load_and_insert(
                str(save_path),
                document_id=saved_document_id,
                room_id=room_id,
                upload_context="document"
            )

            if inserted_document_id is None:
                return {
                    "status": "error",
                    "room_id": room_id,
                    "document_id": saved_document_id,
                    "filename": filename,
                    "saved_path": str(save_path),
                    "message": "문서는 업로드됐지만 ChromaDB 적재에 실패했습니다.",
                    "error": "chroma_insert_failed"
                }

            message = "문서 업로드 및 ChromaDB 적재 완료"

        elif suffix in {".png", ".jpg", ".jpeg"}:
            message = "이미지 업로드 완료, OCR 처리는 추후 연동 예정"

        elif file.content_type and file.content_type.startswith("audio/"):
            message = "음성 파일 업로드 완료, Whisper 처리는 추후 연동 예정"

        else:
            message = "파일 업로드 완료"

        # 10. 성공 결과 반환
        return {
            "status": "success",
            "room_id": room_id,
            "document_id": saved_document_id,
            "filename": filename,
            "saved_path": str(save_path),
            "message": message,
            "error": None
        }

    except Exception as e:
        return {
            "status": "error",
            "room_id": room_id,
            "document_id": None,
            "filename": file.filename if file else None,
            "saved_path": None,
            "message": "문서 업로드 또는 처리 중 오류가 발생했습니다.",
            "error": str(e)
        }