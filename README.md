# CodeRAG — Retrieval-Augmented Q&A for C++ Codebases

Ask natural-language questions about a C++ codebase and get answers grounded in the actual source code, with file:line citations you can verify.

Built against [nlohmann/json](https://github.com/nlohmann/json) as the demo target.

## How it works
1. **Chunking** (`chunker.py`) — splits C++ source into function/class-level chunks using brace-matching
2. **Embedding + indexing** (`build_index.py`) — embeds every chunk locally with `sentence-transformers`, builds a FAISS vector index
3. **Retrieval + generation** (`main.py`) — FastAPI backend: embeds the question, retrieves top-5 relevant chunks, sends them + the question to Groq's free LLM API, returns a cited answer
4. **Frontend** (`index.html`) — plain HTML/JS UI, no build step

## Setup

```bash
# 1. Clone this repo, then create a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Clone the target C++ repo into data/
mkdir data
git clone --depth 1 https://github.com/nlohmann/json.git data/nlohmann-json

# 4. Get a free Groq API key at console.groq.com, then create .env:
#    GROQ_API_KEY=gsk_your_key_here

# 5. Build the index (embeds ~876 code chunks, takes 1-3 min)
cd backend
python build_index.py

# 6. Run the server
uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000** and ask a question.

## Project structure
```
codebase-rag-kit/
├── requirements.txt
├── .env                  # not committed — holds GROQ_API_KEY
├── data/                 # not committed — cloned target repo
├── backend/
│   ├── chunker.py        # C++-aware code chunking
│   ├── build_index.py    # embed + build FAISS index (run once)
│   ├── main.py           # FastAPI: retrieval + generation
│   └── index_store/      # not committed — generated FAISS index
└── frontend/
    └── index.html        # single-page UI
```

## Notes / limitations
- Chunker uses brace-matching, not a real parser — works well for straightforward function/class code but can misparse heavily templated or macro-heavy code.
- Retrieval is pure vector similarity — no re-ranking step yet.
- No streaming responses — the answer appears all at once.
- Groq's free-tier available models change over time; if you get a "model not found" error, check available models for your key at `https://api.groq.com/openai/v1/models`.

## Roadmap
- [ ] Dockerize
- [ ] Split into microservices (embedding / retrieval / generation / gateway)
- [ ] Deploy to GCP Cloud Run
- [ ] Benchmark script: RAG vs no-RAG accuracy and latency