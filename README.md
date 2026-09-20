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
```
                    ┌─────────────┐
   question ───────▶│   Gateway   │◀─────── browser (frontend/)
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼             ▼
        ┌───────────┐ ┌───────────┐ ┌────────────┐
        │ Embedding │ │ Retrieval │ │ Generation │
        │ (MiniLM)  │▶│  (FAISS)  │▶│   (Groq)   │
        └───────────┘ └───────────┘ └────────────┘
```
Each box is an independent FastAPI microservice with its own Dockerfile, deployed
as its own Railway service and reachable over its own public URL. The gateway
orchestrates the three calls and serves the frontend.

---

## Setup (step by step)

### 1. Open this folder in VS Code
```
File > Open Folder... > select codebase-rag-kit
```

### 2. Create a Python virtual environment
Open a terminal in VS Code (`` Ctrl+` ``) and run:
```bash
python3 -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Clone the target repo into `data/`
```bash
mkdir data
git clone --depth 1 https://github.com/nlohmann/json.git data/nlohmann-json
```

### 5. Get a free Groq API key
Go to https://console.groq.com → sign up (free, no card) → create an API key.

Then in the project root:
```bash
cp .env.example .env
```
Open `.env` and paste your key:
```
GROQ_API_KEY=gsk_your_actual_key_here
```

### 6. Build the index
This chunks the repo, embeds it, and saves the FAISS index to disk. Takes ~1-3 minutes on CPU.
```bash
cd backend
python build_index.py
```
You should see output ending in `Done. Index + metadata saved to ./index_store/`.

### 7. Run the API server
Still inside `backend/`:
```bash
uvicorn main:app --reload --port 8000
```

### 8. Open the app
Go to **http://localhost:8000** in your browser. Type a question or click an example chip.

---

## Project structure
```
codebase-rag-kit/
├── requirements.txt
├── .env.example
├── data/                    # you clone the target repo here (gitignored)
├── backend/
│   ├── chunker.py           # C++-aware code chunking
│   ├── build_index.py       # embed + build FAISS index (run once)
│   ├── main.py              # FastAPI app: retrieval + generation
│   └── index_store/         # generated: FAISS index + chunk metadata
└── frontend/
    └── index.html           # single-page UI, no build step
```

## Trying it on a different repo
1. Clone any other C++ repo into `data/`
2. Set `REPO_PATH` env var before building the index, e.g.:
   ```bash
   REPO_PATH=../data/some-other-repo/src python build_index.py
   ```
3. Restart the server

## Things worth improving (good next steps for your portfolio writeup)
- Chunker is regex/brace-based, not a real parser — it'll misparse some edge cases (macros, templates with nested `<>`). Swapping in `tree-sitter` with the C++ grammar would be a strong "v2" improvement to mention.
- No re-ranking step — currently pure vector similarity. Adding a cross-encoder re-ranker (also free, via `sentence-transformers`) would improve precision on ambiguous queries.
- No streaming — the answer appears all at once. Groq supports streaming; wiring that into the frontend would make the demo feel snappier.
- No persistent chat history / multi-turn — each question is independent right now.

## Deployment

The live demo linked above runs all 4 microservices on **Railway**, each deployed
independently from this repo:

| Service | Role |
|---|---|
| `services/embedding` | Loads `all-MiniLM-L6-v2`, exposes `POST /embed` |
| `services/retrieval` | Loads the FAISS index, exposes `POST /retrieve` |
| `services/generation` | Calls Groq's API with retrieved context, exposes `POST /generate` |
| `services/gateway` | Orchestrates the three calls above, serves the frontend |

Each service has its own Dockerfile and its own Root Directory setting pointed at
its `services/<name>` folder, so Railway builds and deploys them independently.
The gateway reads the other three services' public URLs from environment
variables (`EMBEDDING_URL`, `RETRIEVAL_URL`, `GENERATION_URL`) and calls them
over HTTP — the same pattern you'd use for any real microservices deployment
(ECS, Cloud Run, Kubernetes, etc.), just on infrastructure with a free tier.

**Why Railway and not GCP Cloud Run:** GCP Cloud Run was the original target,
and the microservices split was designed with it in mind. During setup, GCP's
billing verification step failed with an account-setup error
(`OR_BACR2_59`) that turned out to be a known, widely-reported issue —
particularly for accounts in India — with no reliable fix on Google's end at
the time. Rather than block the deployment on a third-party billing system,
the same 4-service architecture was redeployed on Railway instead, which has
no billing-verification step for its free tier. The code and Docker images are
unchanged; only the hosting platform differs, and the same setup would deploy
to Cloud Run, ECS, or any other container platform with no changes beyond the
per-service configuration.

For local development, docker-compose (`docker-compose.yml` in the repo root)
runs all 4 services together on one machine using service-name networking
(e.g. `http://embedding:8001`) instead of public URLs — this is what was used
to build and test the system before deploying it.
