from fastapi import FastAPI

from backend.db.database import init_db
from backend.routers.chat_router import router as chat_router
from backend.routers.rag_router import router as rag_router
from backend.routers.document_router import router as document_router
from backend.routers.notion_router import router as notion_router
from backend.routers.agent_router import router as agent_router
from backend.routers.task_router import router as task_router
from backend.routers.stt_router import router as stt_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AI-Agent-System Backend",
    description="FastAPI backend for AI Agent System",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 서버 실행 시 SQLite DB 테이블 자동 생성
init_db()

app.include_router(chat_router)
app.include_router(rag_router)
app.include_router(document_router)
app.include_router(notion_router)
app.include_router(agent_router)
app.include_router(task_router)
app.include_router(stt_router)

@app.get("/")
def root():
    return {
        "message" : "AI-Agent-System backend is running"
    }