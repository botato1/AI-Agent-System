# Python 3.11 slim 베이스 이미지 사용
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 설치 (필요한 경우)
RUN apt-get update && apt-get install -y \
    gcc \
    curl \ 
    && rm -rf /var/lib/apt/lists/*

# requirements.txt 먼저 복사 후 패키지 설치
# (코드 변경 시 캐시 활용을 위해 분리)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 전체 코드 복사
COPY . .

# storage 폴더 생성 (SQLite, 업로드 파일 저장용)
RUN mkdir -p storage/sqlite storage/uploads

# 포트 개방
EXPOSE 8000

# 서버 실행 (운영 환경용 워커 4개) @@@@@#예시# 서버 GPU환경 확인 필요@@@@@@@@@
CMD ["uvicorn", "backend.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4"]
