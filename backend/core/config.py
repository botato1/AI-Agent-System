import os
from dotenv import load_dotenv


# .env 파일에 적힌 환경변수 값을 불러옴
load_dotenv()


class Settings:
    # 프로젝트 기본 이름
    PROJECT_NAME: str = "AI-Agent-System"

    # SQLite DB 파일 경로
    SQLITE_DB_PATH: str = os.getenv(
        "SQLITE_DB_PATH",
        "storage/sqlite/chat.db"
    )

    # Ollama 서버 주소
    OLLAMA_BASE_URL: str = os.getenv(
        "OLLAMA_BASE_URL",
        "http://localhost:11434"
    )

    # Ollama에서 사용할 모델명
    OLLAMA_MODEL_NAME: str = os.getenv(
        "OLLAMA_MODEL_NAME",
        "qwen2.5"
    )



    # 파일 저장 경로 (NAS 연결 시 활성화)
    # STORAGE_PATH: str = os.getenv("STORAGE_PATH", "storage/uploads")



    # Notion API 관련 값
    NOTION_TOKEN: str | None = os.getenv("NOTION_TOKEN")
    NOTION_DATABASE_ID: str | None = os.getenv("NOTION_DATABASE_ID")


# 다른 파일에서 settings.SQLITE_DB_PATH 이런 식으로 쓰기 위한 객체
settings = Settings()