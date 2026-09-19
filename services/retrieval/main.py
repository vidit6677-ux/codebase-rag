"""
Retrieval Service

Holds the FAISS index. Given a query embedding (a vector, already computed
by the Embedding Service), returns the top-k most similar code chunks.

This service does NOT do embedding itself -- it receives ready-made vectors.
This keeps it lightweight (no torch/sentence-transformers needed here).

Run with: uvicorn main:app --port 8002
"""

import os
import pickle
import faiss
from fastapi import FastAPI
from pydantic import BaseModel

INDEX_DIR = "./index_store"
TOP_K_DEFAULT = 5

app = FastAPI(title="Retrieval Service")

print("Loading FAISS index...")
index = faiss.read_index(os.path.join(INDEX_DIR, "faiss.index"))

print("Loading chunk metadata...")
with open(os.path.join(INDEX_DIR, "metadata.pkl"), "rb") as f:
    metadata = pickle.load(f)

print(f"Retrieval service ready. {len(metadata)} chunks loaded.")


class RetrieveRequest(BaseModel):
    embedding: list[float]
    k: int = TOP_K_DEFAULT


class SourceChunk(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    kind: str
    text: str
    score: float


class RetrieveResponse(BaseModel):
    sources: list[SourceChunk]


@app.post("/retrieve", response_model=RetrieveResponse)
def retrieve(req: RetrieveRequest):
    import numpy as np
    q_emb = np.array([req.embedding], dtype="float32")
    scores, idxs = index.search(q_emb, req.k)

    results = []
    for score, idx in zip(scores[0], idxs[0]):
        if idx == -1:
            continue
        meta = metadata[idx]
        results.append(SourceChunk(**meta, score=float(score)))

    return RetrieveResponse(sources=results)


@app.get("/health")
def health():
    return {"status": "ok", "service": "retrieval", "chunks_loaded": len(metadata)}