# Codebase RAG — nlohmann/json Q&A

Ask natural-language questions about the `nlohmann/json` C++ library and get
answers grounded in the actual source code, with file:line citations you can
expand and inspect.

**🔗 Live demo: https://gateway-production-24f8.up.railway.app**

## How it works
1. `chunker.py` splits the C++ source into function/class-level chunks (brace-matching, not naive line splitting)
2. `build_index.py` embeds every chunk locally (`sentence-transformers`) and builds a FAISS vector index
3. A retrieval step finds the top-k relevant chunks for a question, then an LLM (Groq, free tier) generates a cited answer grounded in those chunks
4. `frontend/index.html` is a plain HTML/JS UI — no build step needed

Everything is free except the LLM call, which uses Groq's free tier (fast, no card required).

### Two ways to run this
- **`backend/`** — a single self-contained FastAPI app (embedding + retrieval + generation in one process). Simplest way to run locally.
- **`services/`** — the same system split into 4 independent microservices (`embedding`, `retrieval`, `generation`, `gateway`), each with its own Dockerfile. This is what's actually deployed live (see [Architecture](#architecture) and [Deployment](#deployment) below).

## Results
Benchmarked RAG vs. no-RAG on 10 questions about the codebase (keyword-match accuracy proxy):

| | Accuracy | Avg. latency |
|---|---|---|
| No RAG (direct to LLM) | 25% | 0.94s |
| **With RAG** | **80%** | 1.10s |

**+55 percentage points of accuracy for ~150ms of extra latency.** See `benchmark/` for the harness and `benchmark/benchmark_results.json` for raw results.

## Architecture