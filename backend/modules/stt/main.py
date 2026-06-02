# main.py
from fastapi import FastAPI
from routers import stt

app = FastAPI(title="VoiceCatch API 서버")

# 라우터 연결 (이 한 줄로 routers/stt.py 내부의 API가 서버에 등록됩니다)
app.include_router(stt.router)

@app.get("/")
def root():
    return {"message": "서버가 정상적으로 실행 중입니다!"}