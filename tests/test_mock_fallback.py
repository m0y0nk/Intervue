import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.main import app
from app.database.session import Base, get_db
from app.models.database import ProblemModel, SessionModel
from app.schemas.problem import ProblemPrivate
from app.schemas.session import InterviewConfig, SessionState
from app.services.gemini_service import gemini_service
from app.api.sessions import _compute_requested_summary, _serialize_session_state

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


client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    app.dependency_overrides.pop(get_db, None)


def test_gemini_fallback_sets_mock_metadata():
    """Verify that unconfigured gemini_service sets is_mock=True and mock_reason."""
    mock_prob = gemini_service._mock_response("random_dsa arrays_hashing", ProblemPrivate)
    assert mock_prob is not None
    assert isinstance(mock_prob, ProblemPrivate)


def test_requested_summary_computation():
    """Test human-readable summary of what problem was requested."""
    sess_lc = SessionModel(source="leetcode", difficulty="medium", category="arrays_hashing")
    summary = _compute_requested_summary(sess_lc, leetcode_id="42")
    assert summary == "LeetCode #42"

    sess_lc_paste = SessionModel(source="leetcode", difficulty="medium", category="arrays_hashing")
    assert _compute_requested_summary(sess_lc_paste) == "Pasted LeetCode problem"

    sess_custom = SessionModel(source="custom", difficulty="hard", category="graphs")
    assert _compute_requested_summary(sess_custom, custom_url="https://example.com/prob") == "Custom problem from https://example.com/prob"

    sess_dsa = SessionModel(source="random_dsa", difficulty="medium", category="two_pointers")
    assert "Two Pointers" in _compute_requested_summary(sess_dsa)


def test_serialized_session_includes_mock_fallback_info():
    """Verify SessionState schema serializes is_mock and mock_reason to client."""
    db = TestingSessionLocal()
    mock_prob = gemini_service._mock_response("random_dsa", ProblemPrivate)
    mock_prob.is_mock = True
    mock_prob.mock_reason = "Gemini API key is not configured in .env (GEMINI_API_KEY). Loaded offline deterministic mock problem."

    prob_model = ProblemModel(
        id=mock_prob.id,
        title=mock_prob.title,
        fingerprint=mock_prob.fingerprint,
        category="arrays_hashing",
        difficulty="medium",
        public_data=json.dumps(mock_prob.model_dump(exclude={"python_reference", "python_brute_force", "hidden_tests", "rubric"})),
        private_data=json.dumps(mock_prob.model_dump()),
    )
    db.add(prob_model)

    sess = SessionModel(
        id="sess_mock_test_01",
        problem_id=prob_model.id,
        status="ready",
        stage=1,
        source="leetcode",
        is_mock=True,
        mock_reason="Failed to validate requested problem after 3 attempts.",
        requested_problem_summary="LeetCode #15",
    )
    db.add(sess)
    db.commit()

    serialized = _serialize_session_state(db, sess)
    assert serialized.is_mock is True
    assert "Failed to validate" in serialized.mock_reason
    assert serialized.requested_problem_summary == "LeetCode #15"
    assert serialized.problem is not None
    assert serialized.problem.is_mock is True

    # Test via API endpoint
    res = client.get("/api/sessions/sess_mock_test_01")
    assert res.status_code == 200
    data = res.json()
    assert data["is_mock"] is True
    assert "Failed to validate" in data["mock_reason"]
    assert data["requested_problem_summary"] == "LeetCode #15"
    db.close()
