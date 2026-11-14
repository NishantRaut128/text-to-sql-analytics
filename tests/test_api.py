from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ask_rejects_question_shorter_than_five_characters():
    response = client.post("/ask", json={"question": "hi"})
    assert response.status_code == 422


def test_ask_rejects_question_longer_than_500_characters():
    response = client.post("/ask", json={"question": "x" * 501})
    assert response.status_code == 422


def test_ask_rejects_missing_question():
    response = client.post("/ask", json={})
    assert response.status_code == 422
