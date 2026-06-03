# SQLite 데이터베이스 연결 관리
import sqlite3
from pathlib import Path

from backend.core.config import settings

# SQLite DB 연결을 관리하는 함수
def get_connection():
    db_path = Path(settings.SQLITE_DB_PATH)

    # storage/sqlite 폴더가 없으면 자동 생성
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    return conn