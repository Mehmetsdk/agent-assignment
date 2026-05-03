from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Dict
from src.agent import TaskAgent

app = FastAPI()

# Allow cross-origin requests for local development (e.g., Live Server on :5500)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500", "http://127.0.0.1:8001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="web"), name="static")

class ChatRequest(BaseModel):
    message: str

agent = TaskAgent()


@app.get("/", response_class=HTMLResponse)
async def landing():
    """Landing page with a Go Live button that navigates to the chat UI."""
    with open("web/landing.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/chat", response_class=HTMLResponse)
async def chat_page():
    with open("web/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.post("/api/chat")
async def chat(req: ChatRequest):
    resp = agent.process_input(req.message)
    return {"reply": resp}
