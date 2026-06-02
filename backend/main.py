from fastapi import FastAPI

app = FastAPI(
    title="AI-Agent-System Backend",
    description="FastAPI backend for AI Agent System",
    version="0.1.0"
)

@app.get("/")
def root():
    return {
        "message" : "AI-Agent-System backend is running"
    }