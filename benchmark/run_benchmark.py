"""
run_benchmark.py

Compares RAG vs no-RAG for the codebase Q&A system:
- Latency (time to answer)
- Accuracy (does the answer mention expected key facts)

Run with the gateway services running (embedding:8001, retrieval:8002,
generation:8003) OR with docker-compose up.

Usage: python run_benchmark.py
"""

import time
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = "openai/gpt-oss-20b"

EMBEDDING_URL = "http://localhost:8001"
RETRIEVAL_URL = "http://localhost:8002"
GENERATION_URL = "http://localhost:8003"

TEST_CASES = [
    {
        "question": "How does the parser detect JSON errors?",
        "expected_keywords": ["parse_error", "sax"],
    },
    {
        "question": "How is comparison between JSON values implemented?",
        "expected_keywords": ["operator==", "compare"],
    },
    {
        "question": "How does the library handle Unicode strings?",
        "expected_keywords": ["utf", "unicode"],
    },
    {
        "question": "What class represents a JSON value?",
        "expected_keywords": ["basic_json"],
    },
    {
        "question": "How does the library serialize a JSON object to a string?",
        "expected_keywords": ["dump", "serializer"],
    },
    {
        "question": "What happens when you access a missing key in a JSON object?",
        "expected_keywords": ["out_of_range", "exception"],
    },
    {
        "question": "How does the library support binary formats like CBOR or MessagePack?",
        "expected_keywords": ["cbor", "msgpack", "binary_reader"],
    },
    {
        "question": "What is adl_serializer used for?",
        "expected_keywords": ["adl_serializer", "to_json", "from_json"],
    },
    {
        "question": "How does the library implement iterators over JSON values?",
        "expected_keywords": ["iterator"],
    },
    {
        "question": "How are exceptions structured in this library?",
        "expected_keywords": ["exception", "json_exception"],
    },
]


def score_answer(answer, expected_keywords):
    answer_lower = answer.lower()
    hits = sum(1 for kw in expected_keywords if kw.lower() in answer_lower)
    return hits / len(expected_keywords) if expected_keywords else 0.0


def ask_no_rag(question):
    start = time.time()
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": question}],
            "temperature": 0.2,
            "max_tokens": 500,
        },
        timeout=30,
    )
    elapsed = time.time() - start
    if resp.status_code != 200:
        return f"[ERROR: {resp.status_code} - {resp.text[:200]}]", elapsed
    answer = resp.json()["choices"][0]["message"]["content"]
    return answer, elapsed


def ask_with_rag(question):
    start = time.time()

    embed_resp = requests.post(f"{EMBEDDING_URL}/embed", json={"text": question}, timeout=30)
    embedding = embed_resp.json()["embedding"]

    retrieve_resp = requests.post(
        f"{RETRIEVAL_URL}/retrieve", json={"embedding": embedding, "k": 5}, timeout=30
    )
    sources = retrieve_resp.json()["sources"]

    generate_resp = requests.post(
        f"{GENERATION_URL}/generate",
        json={"question": question, "sources": sources},
        timeout=60,
    )
    elapsed = time.time() - start

    if generate_resp.status_code != 200:
        return f"[ERROR: {generate_resp.status_code} - {generate_resp.text[:200]}]", elapsed
    answer = generate_resp.json()["answer"]
    return answer, elapsed


def main():
    print(f"Running benchmark on {len(TEST_CASES)} questions...\n")
    print(f"{'Question':<55} {'No-RAG Score':<14} {'RAG Score':<12} {'No-RAG Time':<13} {'RAG Time':<10}")
    print("-" * 110)

    no_rag_scores = []
    rag_scores = []
    no_rag_times = []
    rag_times = []

    for case in TEST_CASES:
        question = case["question"]
        keywords = case["expected_keywords"]

        no_rag_answer, no_rag_time = ask_no_rag(question)
        time.sleep(8)
        rag_answer, rag_time = ask_with_rag(question)
        time.sleep(8)

        no_rag_score = score_answer(no_rag_answer, keywords)
        rag_score = score_answer(rag_answer, keywords)

        no_rag_scores.append(no_rag_score)
        rag_scores.append(rag_score)
        no_rag_times.append(no_rag_time)
        rag_times.append(rag_time)

        q_short = (question[:52] + "...") if len(question) > 52 else question
        print(f"{q_short:<55} {no_rag_score:<14.2f} {rag_score:<12.2f} {no_rag_time:<13.2f} {rag_time:<10.2f}")

    print("-" * 110)
    avg_no_rag_score = sum(no_rag_scores) / len(no_rag_scores)
    avg_rag_score = sum(rag_scores) / len(rag_scores)
    avg_no_rag_time = sum(no_rag_times) / len(no_rag_times)
    avg_rag_time = sum(rag_times) / len(rag_times)

    print(f"\nSUMMARY")
    print(f"Average accuracy score  -- No-RAG: {avg_no_rag_score:.2%}   RAG: {avg_rag_score:.2%}")
    print(f"Average latency (sec)   -- No-RAG: {avg_no_rag_time:.2f}s   RAG: {avg_rag_time:.2f}s")
    print(f"\nRAG improved accuracy by {(avg_rag_score - avg_no_rag_score):.2%} percentage points")
    print(f"RAG added {(avg_rag_time - avg_no_rag_time):.2f}s of latency on average")

    results = {
        "test_cases": len(TEST_CASES),
        "avg_no_rag_score": avg_no_rag_score,
        "avg_rag_score": avg_rag_score,
        "avg_no_rag_time": avg_no_rag_time,
        "avg_rag_time": avg_rag_time,
    }
    with open("benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nResults saved to benchmark_results.json")


if __name__ == "__main__":
    main()