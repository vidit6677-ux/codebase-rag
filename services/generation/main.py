"""
Generation Service

Given a question and a list of retrieved source chunks, builds a prompt
and calls Groq's API to generate a grounded, cited answer.

Run with: uvicorn main:app --port 8003
"""

import os
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = "openai/gpt-oss-20b"

app = FastAPI(title="Generation Service")


class SourceChunk(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    kind: str
    text: str
    score: float


class GenerateRequest(BaseModel):
    question: str
    sources: list[SourceChunk]


class GenerateResponse(BaseModel):
    answer: str


def build_prompt(question: str, sources: list[SourceChunk]) -> str:
    context_blocks = []
    for i, s in enumerate(sources):
        context_blocks.append(
            f"[Source {i+1}: {s.file_path}:{s.start_line}-{s.end_line}]\n{s.text}"
        )
    context = "\n\n".join(context_blocks)
    return f"""You are a C++ codebase expert answering questions about the nlohmann/json library.
Use ONLY the code excerpts below to answer. Cite sources by their number (e.g. "[Source 2]") when referencing specific code.
If the excerpts don't contain enough information to answer, say so directly instead of guessing.

CODE EXCERPTS:
{context}

QUESTION: {question}

ANSWER:"""


@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not set.")

    prompt = build_prompt(req.question, req.sources)

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
    answer = data["choices"][0]["message"]["content"]
    return GenerateResponse(answer=answer)


@app.get("/health")
def health():
    return {"status": "ok", "service": "generation"}