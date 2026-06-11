import os
import logging
import platform

# 기본 디렉토리 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

# 운영체제별 확장자 처리 (Windows는 .exe 포함)
EXE_EXT = ".exe" if platform.system() == "Windows" else ""

# AI 엔진 및 스크립트 경로
WHISPER_CLI = os.path.join(BASE_DIR, "whisper.cpp", "build", "bin", f"whisper-cli{EXE_EXT}")
WHISPER_MODEL = os.path.join(BASE_DIR, "whisper.cpp", "models", "ggml-large-v3-turbo.bin")
DIARIZE_SCRIPT = os.path.join(BASE_DIR, "diarize_engine.py")

# OS별 파이썬 가상환경 경로 분기
if platform.system() == "Windows":
    PYTHON_EXEC = os.path.join(BASE_DIR, "venv", "Scripts", "python.exe")
else:
    PYTHON_EXEC = os.path.join(BASE_DIR, "venv", "bin", "python3")

# uploads 폴더 자동 생성
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 로거 설정
logger = logging.getLogger("vigo_project")
logger.setLevel(logging.INFO)