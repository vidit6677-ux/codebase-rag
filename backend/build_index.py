"""
build_index.py

Chunks the repo, embeds every chunk locally, builds a FAISS index,
and saves it to disk for main.py to load at startup.
"""

import os
import json
import pickle
import faiss
from sentence_transformers import SentenceTransformer

from chunker import chunk_repo

REPO_PATH = os.environ.get("REPO_PATH", "../data/nlohmann-json/include")
INDEX_DIR = "./index_store"
EMBED_MODEL = "all-MiniLM-L6-v2"


def main():
    os.makedirs(INDEX_DIR, exist_ok=True)

    print(f"Chunking repo at {REPO_PATH} ...")
    chunks = chunk_repo(REPO_PATH)
    print(f"  -> {len(chunks)} chunks")

    if len(chunks) == 0:
        raise SystemExit("No chunks found. Check REPO_PATH.")

    print(f"Loading embedding model: {EMBED_MODEL} ...")
    model = SentenceTransformer(EMBED_MODEL)

    texts = [c.text for c in chunks]
    print(f"Embedding {len(texts)} chunks (this may take a minute)...")
    embeddings = model.encode(
        texts,
        batch_size=64,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype("float32")

    dim = embeddings.shape[1]
    print(f"Building FAISS index (dim={dim}) ...")
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    faiss.write_index(index, os.path.join(INDEX_DIR, "faiss.index"))

    metadata = [
        {
            "file_path": c.file_path,
            "start_line": c.start_line,
            "end_line": c.end_line,
            "kind": c.kind,
            "text": c.text,
        }
        for c in chunks
    ]
    with open(os.path.join(INDEX_DIR, "metadata.pkl"), "wb") as f:
        pickle.dump(metadata, f)

    with open(os.path.join(INDEX_DIR, "config.json"), "w") as f:
        json.dump({"embed_model": EMBED_MODEL, "num_chunks": len(chunks), "repo_path": REPO_PATH}, f, indent=2)

    print(f"Done. Index + metadata saved to {INDEX_DIR}/")


if __name__ == "__main__":
    main()