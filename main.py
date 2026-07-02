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
    metrics: dict = {}

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
        
        # Calculate dynamic evaluation metrics for this turn
        recs = result.get("recommendations", [])
        
        # Groundedness & Hallucination checks against catalog database
        from catalog import CATALOG
        valid_names = {item["name"] for item in CATALOG}
        
        total_recs = len(recs)
        valid_recs = sum(1 for r in recs if r.get("name") in valid_names)
        
        groundedness_score = 100.0 if (total_recs == 0 or valid_recs == total_recs) else (valid_recs / total_recs * 100.0)
        hallucination_rate = 0.0 if (total_recs == 0 or valid_recs == total_recs) else ((total_recs - valid_recs) / total_recs * 100.0)
        
        # Extract states
        state = result.get("state", {})
        role_state = state.get("job_role")
        seniority_state = state.get("seniority")
        intent_state = state.get("intent", "HIRING")
        
        # Confidence score (100% when active, 0% when clarifying/greeting)
        retrieval_confidence = 100.0 if (total_recs > 0) else 0.0
        
        metrics = {
            "groundedness": groundedness_score,
            "hallucination_rate": hallucination_rate,
            "role": role_state,
            "seniority": seniority_state,
            "intent": intent_state,
            "confidence": retrieval_confidence
        }
        
        return ChatResponse(
            reply=result["reply"],
            recommendations=recs,
            end_of_conversation=result.get("end_of_conversation", False),
            metrics=metrics
        )
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(
            status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
