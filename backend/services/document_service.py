# 문서 업로드 및 처리 서비스
from pathlib import Path
from fastapi import UploadFile

from backend.modules.rag.document_loader import load_and_insert


# 프로젝트 루트 기준 data/raw 경로
BASE_DIR = Path(__file__).resolve().parents[2]
UPLOAD_DIR = BASE_DIR / "data" / "raw"


# 문서 업로드 후 ChromaDB에 바로 적재하는 함수
async def upload_and_process_document(file: UploadFile,room_id: str) -> dict:
    try:
        # 1. 업로드 폴더가 없으면 생성
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        # 2. 파일 저장 경로 생성
        save_path = UPLOAD_DIR / file.filename

        # 3. 업로드된 파일 내용 읽기
        file_content = await file.read()

        # 4. 파일 저장
        with open(save_path, "wb") as f:
            f.write(file_content)

        # 5. 저장된 파일 하나만 ChromaDB에 적재
        load_and_insert(str(save_path))

        # 6. 성공 결과 반환
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