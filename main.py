from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List
import logging
import os
from agent import process

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Enable CORS for frontend clients (like test_ui.html)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

class Recommendation(BaseModel):
    name: str
    url: str
    test_type: str

class ChatResponse(BaseModel):
    reply: str
    recommendations: List[Recommendation] = []
    end_of_conversation: bool = False

@app.get("/", response_class=HTMLResponse)
def read_index():
    path = os.path.join(os.path.dirname(__file__), "test_ui.html")
    if not os.path.exists(path):
        path = "test_ui.html"
    with open(path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content, status_code=200)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    logger.info(f"Received {len(request.messages)} messages")
    try:
        messages = [
            {"role": m.role, "content": m.content}
            for m in request.messages
        ]
        result = process(messages)
        return ChatResponse(
            reply=result["reply"],
            recommendations=result.get(
                "recommendations", []),
            end_of_conversation=result.get(
                "end_of_conversation", False)
        )
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(
            status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
