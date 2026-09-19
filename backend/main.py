"""
main.py

FastAPI app: loads the FAISS index, retrieves relevant code chunks for a
question, sends them to Groq's free LLM API for a cited answer, and serves
the frontend.

Run with: uvicorn main:app --reload --port 8000
"""

import os
import pickle
import requests
import faiss
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

INDEX_DIR = "./index_store"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = "openai/gpt-oss-20b"
TOP_K = 5

app = FastAPI(title="Codebase RAG - nlohmann/json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

print("Loading embedding model...")
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

print("Loading FAISS index...")
index = faiss.read_index(os.path.join(INDEX_DIR, "faiss.index"))

print("Loading chunk metadata...")
with open(os.path.join(INDEX_DIR, "metadata.pkl"), "rb") as f:
    metadata = pickle.load(f)

print(f"Ready. {len(metadata)} chunks loaded.")


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


def retrieve(question: str, k: int = TOP_K):
    q_emb = embed_model.encode([question], normalize_embeddings=True, convert_to_numpy=True).astype("float32")
    scores, idxs = index.search(q_emb, k)
    results = []
    for score, idx in zip(scores[0], idxs[0]):
        if idx == -1:
            continue
        meta = metadata[idx]
        results.append({**meta, "score": float(score)})
    return results


def build_prompt(question: str, sources: list) -> str:
    context_blocks = []
    for i, s in enumerate(sources):
        context_blocks.append(
            f"[Source {i+1}: {s['file_path']}:{s['start_line']}-{s['end_line']}]\n{s['text']}"
        )
    context = "\n\n".join(context_blocks)
    return f"""You are a C++ codebase expert answering questions about the nlohmann/json library.
Use ONLY the code excerpts below to answer. Cite sources by their number (e.g. "[Source 2]") when referencing specific code.
If the excerpts don't contain enough information to answer, say so directly instead of guessing.

CODE EXCERPTS:
{context}

QUESTION: {question}

ANSWER:"""


def call_groq(prompt: str) -> str:
    if not GROQ_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY not set. Get a free key at console.groq.com and put it in your .env file.",
        )
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 800,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Groq API error: {resp.status_code} {resp.text}")
    data = resp.json()
    return data["choices"][0]["message"]["content"]


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    sources = retrieve(req.question, k=TOP_K)
    prompt = build_prompt(req.question, sources)
    answer = call_groq(prompt)

    return QueryResponse(
        answer=answer,
        sources=[SourceChunk(**s) for s in sources],
    )


@app.get("/health")
def health():
    return {"status": "ok", "chunks_loaded": len(metadata)}


app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")