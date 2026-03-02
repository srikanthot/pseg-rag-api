import logging
import traceback
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .rag import answer as rag_answer

logging.basicConfig(level="INFO")
logger = logging.getLogger(__name__)

app = FastAPI(title="RAG Chatbot API", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    top_k: Optional[int] = None
    chat_history: Optional[list] = None


class CitationOut(BaseModel):
    title: str
    url: str
    page: Optional[int] = None


class ChatResponse(BaseModel):
    answer: str
    citations: list[CitationOut]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        answer_text, citations = rag_answer(req.question, top_k=req.top_k, chat_history=req.chat_history)
        return ChatResponse(
            answer=answer_text,
            citations=[CitationOut(title=c.title, url=c.url, page=c.page) for c in citations],
        )
    except Exception as e:
        logger.error("Chat error: %s\n%s", e, traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
