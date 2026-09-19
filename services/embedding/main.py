"""
Embedding Service

A tiny FastAPI app whose only job is: given text, return its vector embedding.
This isolates the sentence-transformers model so it can be scaled/deployed
independently of retrieval and generation.

Run with: uvicorn main:app --port 8001
"""

from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

app = FastAPI(title="Embedding Service")

print("Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")
print("Embedding model ready.")


class EmbedRequest(BaseModel):
    text: str


class EmbedResponse(BaseModel):
    embedding: list[float]


@app.post("/embed", response_model=EmbedResponse)
def embed(req: EmbedRequest):
    vector = model.encode(
        [req.text],
        normalize_embeddings=True,
        convert_to_numpy=True,
    )[0]
    return EmbedResponse(embedding=vector.tolist())


@app.get("/health")
def health():
    return {"status": "ok", "service": "embedding"}