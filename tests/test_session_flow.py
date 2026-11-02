import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.main import app
from app.database.session import Base, get_db
from app.models.database import ProblemModel, SessionModel
from app.schemas.problem import ProblemPrivate
from app.services.gemini_service import gemini_service

from sqlalchemy.pool import StaticPool

# Test database using StaticPool so in-memory DB is shared across threads and connections
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_full_session_flow():
    # 1. Seed a validated problem into test DB directly to test deterministic flow
    db = TestingSessionLocal()
    mock_prob = gemini_service._mock_response("", ProblemPrivate)
    problem_model = ProblemModel(
        id=mock_prob.id,
        title=mock_prob.title,
        fingerprint=mock_prob.fingerprint,
        category="arrays_hashing",
        difficulty="medium",
        public_data=json.dumps(mock_prob.model_dump(exclude={"python_reference", "python_brute_force", "hidden_tests", "rubric"})),
        private_data=json.dumps(mock_prob.model_dump()),
    )
    db.merge(problem_model)

    session = SessionModel(
        id="test_sess_01",
        problem_id=mock_prob.id,
        status="ready",
        stage=1,
        source="random_dsa",
        mode="standard",
        style="general",
        category="arrays_hashing",
        language="python",
        code=mock_prob.starter_code.get("python", ""),
    )
    db.merge(session)
    db.commit()
    db.close()

    # 2. Get session details
    resp = client.get("/api/sessions/test_sess_01")
    assert resp.status_code == 200
    state = resp.json()
    assert state["status"] == "ready"
    assert state["stage"] == 1
    # Stage 1: revealed constraints must be empty
    assert len(state["problem"]["revealed_constraints"]) == 0

    # 3. Begin session
    resp = client.post("/api/sessions/test_sess_01/begin")
    assert resp.status_code == 200
    assert resp.json()["status"] == "running"

    # 4. Chat with interviewer in Stage 1
    resp = client.post(
        "/api/sessions/test_sess_01/interviewer",
        json={"message": "Can nums have negative numbers or duplicates?"},
    )
    assert resp.status_code == 200
    assert "message" in resp.json()

    # 5. Advance through stages
    # Stage 1 -> 2 (Brute force)
    resp = client.post("/api/sessions/test_sess_01/stage/next")
    assert resp.status_code == 200
    assert resp.json()["stage"] == 2

    # Stage 2 -> 3 (Constraint analysis)
    resp = client.post("/api/sessions/test_sess_01/stage/next")
    assert resp.status_code == 200
    assert resp.json()["stage"] == 3
    # In Stage 3, constraints are revealed!
    assert len(resp.json()["problem"]["revealed_constraints"]) > 0

    # Stage 3 -> 4 (Optimal approach)
    resp = client.post("/api/sessions/test_sess_01/stage/next")
    assert resp.json()["stage"] == 4

    # Stage 4 -> 5 (Edge cases)
    resp = client.post("/api/sessions/test_sess_01/stage/next")
    assert resp.json()["stage"] == 5

    # Stage 5 -> 6 (Coding)
    resp = client.post("/api/sessions/test_sess_01/stage/next")
    assert resp.json()["stage"] == 6

    # 6. Verify interviewer is BLOCKED with 409 in Stage 6 (Coding)
    resp = client.post(
        "/api/sessions/test_sess_01/interviewer",
        json={"message": "Can you give me a clue?"},
    )
    assert resp.status_code == 409

    # 7. Update code with valid solution
    valid_code = """
def two_sum(nums, target):
    seen = {}
    for i, x in enumerate(nums):
        diff = target - x
        if diff in seen:
            return [seen[diff], i]
        seen[x] = i
    return []
"""
    resp = client.put(
        "/api/sessions/test_sess_01/code",
        json={"code": valid_code, "language": "python"},
    )
    assert resp.status_code == 200

    # 8. Run visible tests
    resp = client.post("/api/sessions/test_sess_01/run")
    assert resp.status_code == 200
    run_data = resp.json()
    assert run_data["all_passed"] is True
    assert len(run_data["results"]) == 2

    # 9. Submit solution (runs hidden tests once)
    resp = client.post("/api/sessions/test_sess_01/submit")
    assert resp.status_code == 200
    submit_data = resp.json()
    assert submit_data["status"] == "completed"
    assert submit_data["passed_count"] == submit_data["total_count"]
    assert submit_data["coding_score"] == 10.0

    # 10. Fetch report
    resp = client.get("/api/sessions/test_sess_01/report")
    assert resp.status_code == 200
    report = resp.json()
    assert report["total_score"] >= 7.0
    assert report["verdict"] in ("hire", "strong_hire")
    assert len(report["dimension_scores"]) == 10
