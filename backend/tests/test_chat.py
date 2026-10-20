import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_ask_question_validation_empty():
    response = client.post("/api/ask-question", json={"question": ""})
    assert response.status_code == 400
    assert "cannot be empty" in response.json()["detail"].lower()


def test_ask_question_nonexistent_paper():
    response = client.post("/api/ask-question", json={"paper_id": 999999, "question": "What is this?"})
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_ask_question_single_paper():
    # Fetch existing papers
    papers_res = client.get("/api/papers")
    assert papers_res.status_code == 200
    papers = papers_res.json()["papers"]
    
    if papers:
        paper_id = papers[0]["id"]
        response = client.post("/api/ask-question", json={
            "paper_id": paper_id,
            "question": "What are microservices?"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["paper_id"] == paper_id
        assert "answer" in data
        assert "confidence" in data["answer"]
        assert len(data["answer"]["evidence"]) > 0


def test_ask_question_all_papers():
    response = client.post("/api/ask-question", json={
        "question": "What is the main topic of the research?"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "answer" in data
    assert "evidence" in data["answer"]
