from fastapi import FastAPI

from backend.routers.chat_router import router as chat_router
from backend.routers.rag_router import router as rag_router

app = FastAPI(
    title="AI-Agent-System Backend",
    description="FastAPI backend for AI Agent System",
    version="0.1.0"
)

app.include_router(chat_router)
app.include_router(rag_router)

@app.get("/")
def root():
    return {
        "message" : "AI-Agent-System backend is running"
    }