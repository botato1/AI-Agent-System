# 문서 업로드 및 처리 서비스
from pathlib import Path
from fastapi import UploadFile

from backend.modules.rag.document_loader import load_and_insert

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

        if suffix == ".pdf":
            load_and_insert(str(save_path))
            message = "문서 업로드 및 ChromaDB 적재 완료"
        elif suffix in {".png", ".jpg", ".jpeg"}:
            message = "이미지 업로드 완료, OCR 처리는 추후 연동 예정"
        elif file.content_type and file.content_type.startswith("audio/"):
            message = "음성 파일 업로드 완료, Whisper 처리는 추후 연동 예정"
        else:
            message = "파일 업로드 완료"
       
        # 7. 성공 결과 반환
        return {
            "status": "success",
            "room_id": room_id,
            "filename": file.filename,
            "saved_path": str(save_path),
            "message": "문서 업로드 및 ChromaDB 적재 완료",
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