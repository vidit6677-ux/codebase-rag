from fastapi.testclient import TestClient

from services.gateway.main import app


def test_health_returns_ok():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "gateway"}


def test_query_rejects_blank_question_without_calling_services():
    with TestClient(app) as client:
        response = client.post("/query", json={"question": "   "})

    assert response.status_code == 400
    assert response.json()["detail"] == "Question cannot be empty."
