"""
Gateway Service

The single entry point for the frontend. Receives a question, orchestrates
calls to the Embedding, Retrieval, and Generation services in sequence,
and returns the final answer + sources to the browser.

Run with: uvicorn main:app --port 8000
"""

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

EMBEDDING_URL = "http://localhost:8001"
RETRIEVAL_URL = "http://localhost:8002"
GENERATION_URL = "http://localhost:8003"

app = FastAPI(title="Gateway Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    question: str


class SourceChunk(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    kind: str
    text: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # 1. Embed the question
    embed_resp = requests.post(f"{EMBEDDING_URL}/embed", json={"text": req.question}, timeout=30)
    if embed_resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Embedding service error: {embed_resp.text}")
    embedding = embed_resp.json()["embedding"]

    # 2. Retrieve relevant chunks
    retrieve_resp = requests.post(
        f"{RETRIEVAL_URL}/retrieve", json={"embedding": embedding, "k": 5}, timeout=30
    )
    if retrieve_resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Retrieval service error: {retrieve_resp.text}")
    sources = retrieve_resp.json()["sources"]

    # 3. Generate the answer
    generate_resp = requests.post(
        f"{GENERATION_URL}/generate",
        json={"question": req.question, "sources": sources},
        timeout=60,
    )
    if generate_resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Generation service error: {generate_resp.text}")
    answer = generate_resp.json()["answer"]

    return QueryResponse(answer=answer, sources=[SourceChunk(**s) for s in sources])


@app.get("/health")
def health():
    return {"status": "ok", "service": "gateway"}


app.mount("/", StaticFiles(directory="../../frontend", html=True), name="frontend")