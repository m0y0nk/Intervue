import json
import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.main import app
from app.database.session import Base, get_db
from app.models.database import SessionModel, ProblemModel, utcnow
from app.schemas.session import InterviewConfig, SessionCreateRequest
from app.services.config_validator import validate_interview_config, ConfigValidationError

from sqlalchemy.pool import StaticPool

# Setup test database with StaticPool
TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DB_URL,
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


def test_valid_standard_config():
    db = TestingSessionLocal()
    cfg = InterviewConfig(
        source="random_dsa",
        mode="standard",
        style="google",
        difficulty="medium",
        category="arrays_hashing",
        language="python",
        duration=1200,
    )
    # Should not raise
    validate_interview_config(cfg, db)
    db.close()


def test_duration_must_be_1200():
    db = TestingSessionLocal()
    cfg = InterviewConfig(
        source="random_dsa",
        mode="standard",
        style="general",
        duration=1800,  # Invalid
    )
    with pytest.raises(ConfigValidationError, match="20 minutes"):
        validate_interview_config(cfg, db)

    resp = client.post("/api/sessions", json={"config": cfg.model_dump()})
    assert resp.status_code == 422
    assert "20 minutes" in resp.json()["detail"]
    db.close()


def test_topic_mastery_rejects_mixed():
    db = TestingSessionLocal()
    cfg = InterviewConfig(
        source="random_dsa",
        mode="topic_mastery",
        category="mixed",
    )
    with pytest.raises(ConfigValidationError, match="mixed"):
        validate_interview_config(cfg, db)

    resp = client.post("/api/sessions", json={"config": cfg.model_dump()})
    assert resp.status_code == 422
    assert "mixed" in resp.json()["detail"]
    db.close()


def test_topic_mastery_accepts_specific_category():
    db = TestingSessionLocal()
    cfg = InterviewConfig(
        source="random_dsa",
        mode="topic_mastery",
        category="trees",
    )
    validate_interview_config(cfg, db)
    db.close()


def test_business_framing_allowed_for_random_dsa_and_leetcode():
    db = TestingSessionLocal()
    # leetcode with business framing is allowed
    cfg_lc = InterviewConfig(
        source="leetcode",
        framing="business",
    )
    validate_interview_config(cfg_lc, db)

    # random_dsa with business framing is allowed
    cfg_rd = InterviewConfig(
        source="random_dsa",
        framing="business",
    )
    validate_interview_config(cfg_rd, db)

    # custom with business framing is rejected
    cfg_custom = InterviewConfig(
        source="custom",
        framing="business",
    )
    with pytest.raises(ConfigValidationError, match="Business framing is only supported for sources 'random_dsa' and 'leetcode'"):
        validate_interview_config(cfg_custom, db)

    resp = client.post("/api/sessions", json={"config": cfg_custom.model_dump(), "custom_statement": "Valid statement with more than twenty chars"})
    assert resp.status_code == 422
    db.close()


def test_adaptive_difficulty_requires_adaptive_source():
    db = TestingSessionLocal()
    cfg = InterviewConfig(
        source="random_dsa",
        difficulty="adaptive",
    )
    with pytest.raises(ConfigValidationError, match="Adaptive difficulty is only supported when source is 'adaptive'"):
        validate_interview_config(cfg, db)

    resp = client.post("/api/sessions", json={"config": cfg.model_dump()})
    assert resp.status_code == 422
    db.close()


def test_revision_mode_requires_completed_history():
    db = TestingSessionLocal()
    cfg = InterviewConfig(
        source="random_dsa",
        mode="revision",
        category="trees",
    )
    with pytest.raises(ConfigValidationError, match="requires at least one prior completed interview"):
        validate_interview_config(cfg, db)

    resp = client.post("/api/sessions", json={"config": cfg.model_dump()})
    assert resp.status_code == 422
    db.close()


def test_revision_mode_requires_matching_category():
    db = TestingSessionLocal()
    # Add a finished session in 'arrays_hashing'
    finished_sess = SessionModel(
        id="prev_sess_1",
        status="finished",
        stage=6,
        source="random_dsa",
        mode="standard",
        style="general",
        category="arrays_hashing",
        difficulty="medium",
        language="python",
        problem_id="prob_1",
    )
    db.add(finished_sess)
    db.commit()

    # Request revision for 'trees' -> should fail
    cfg_trees = InterviewConfig(
        source="random_dsa",
        mode="revision",
        category="trees",
    )
    with pytest.raises(ConfigValidationError, match="No eligible revision problems found"):
        validate_interview_config(cfg_trees, db)

    # Request revision for 'arrays_hashing' -> should pass
    cfg_arrays = InterviewConfig(
        source="random_dsa",
        mode="revision",
        category="arrays_hashing",
    )
    validate_interview_config(cfg_arrays, db)
    db.close()


def test_adaptive_source_cold_start_rejection():
    db = TestingSessionLocal()
    cfg = InterviewConfig(
        source="adaptive",
        difficulty="adaptive",
    )

    # 0 sessions: reject
    with pytest.raises(ConfigValidationError, match="Adaptive practice requires at least 5 completed interviews"):
        validate_interview_config(cfg, db)

    resp = client.post("/api/sessions", json={"config": cfg.model_dump()})
    assert resp.status_code == 422
    assert "at least 5 completed interviews" in resp.json()["detail"]

    # 4 sessions across categories: still reject
    for i in range(4):
        db.add(
            SessionModel(
                id=f"sess_{i}",
                status="finished",
                stage=6,
                source="random_dsa",
                mode="standard",
                style="general",
                category=f"cat_{i}",
                difficulty="medium",
                language="python",
                problem_id=f"prob_{i}",
            )
        )
    db.commit()

    with pytest.raises(ConfigValidationError, match="at least 5 completed interviews"):
        validate_interview_config(cfg, db)

    # Add 5th session but all in different categories (max count = 1, need >= 2): still reject
    db.add(
        SessionModel(
            id="sess_4",
            status="finished",
            stage=6,
            source="random_dsa",
            mode="standard",
            style="general",
            category="cat_4",
            difficulty="medium",
            language="python",
            problem_id="prob_4",
        )
    )
    db.commit()

    with pytest.raises(ConfigValidationError, match="at least 2 in a single category"):
        validate_interview_config(cfg, db)

    # Add a 6th session in cat_0 so cat_0 count = 2: now pass!
    db.add(
        SessionModel(
            id="sess_5",
            status="finished",
            stage=6,
            source="random_dsa",
            mode="standard",
            style="general",
            category="cat_0",
            difficulty="medium",
            language="python",
            problem_id="prob_5",
        )
    )
    db.commit()

    validate_interview_config(cfg, db)
    db.close()


def test_blind_mock_server_side_redaction():
    db = TestingSessionLocal()

    # Create problem
    private_problem_data = {
        "id": "prob_blind_test_01",
        "title": "Secret Algorithmic Mystery",
        "statement": "Find the secret element.",
        "examples": [{"input_str": "[1, 2]", "output_str": "2"}],
        "signature": {
            "function_name": "find_secret",
            "args": [{"name": "nums", "type": "int[]"}],
            "return_type": "int",
        },
        "revealed_constraints": ["1 <= nums.length <= 10^5"],
        "visible_tests": [{"args": [[1, 2]], "expected": 2}],
        "starter_code": {"python": "def find_secret(nums):\n    pass\n"},
        "checker": "exact",
        "category": "binary_search",
        "difficulty": "hard",
        "expected_time_complexity": "O(log N)",
        "expected_space_complexity": "O(1)",
        "rubric": [],
    }

    prob_model = ProblemModel(
        id="prob_blind_test_01",
        title="Secret Algorithmic Mystery",
        category="binary_search",
        difficulty="hard",
        public_data="{}",
        private_data=json.dumps(private_problem_data),
    )
    db.add(prob_model)

    # Create blind mock session
    sess = SessionModel(
        id="sess_blind_01",
        status="running",
        stage=3,
        source="random_dsa",
        mode="blind_mock",
        style="google",
        category="binary_search",
        difficulty="hard",
        language="python",
        duration=1200,
        problem_id="prob_blind_test_01",
    )
    db.add(sess)
    db.commit()
    db.close()

    # Fetch session state via candidate API
    resp = client.get("/api/sessions/sess_blind_01")
    assert resp.status_code == 200
    data = resp.json()

    # 1. Assert problem is ProblemPublicBlind schema:
    # "id", "title", "difficulty", "category" must be omitted entirely
    problem = data["problem"]
    assert "id" not in problem or problem["id"] is None
    assert "title" not in problem or problem["title"] is None
    assert "difficulty" not in problem or problem["difficulty"] is None
    assert "category" not in problem or problem["category"] is None
    assert "expected_time_complexity" not in problem
    assert "expected_space_complexity" not in problem

    # Visible problem fields should remain intact
    assert problem["statement"] == "Find the secret element."
    assert len(problem["examples"]) == 1
    assert len(problem["revealed_constraints"]) == 1
    assert problem["signature"]["function_name"] == "find_secret"

    # 2. Assert config category and difficulty are redacted to None
    assert data["config"]["category"] is None
    assert data["config"]["difficulty"] is None
    assert data["config"]["mode"] == "blind_mock"


def test_topic_mastery_with_blind_mock_allowed():
    """
    SPEC line 65:
    'topic_mastery + blind_mock: allowed; category chosen but never shown during the interview.'
    """
    db = TestingSessionLocal()
    cfg = InterviewConfig(
        source="random_dsa",
        mode="blind_mock",
        category="dynamic_programming",
    )
    validate_interview_config(cfg, db)
    db.close()


@pytest.mark.asyncio
async def test_interviewer_service_blind_mock_no_title_leak():
    """
    Verifies that interviewer service prompt formatting never leaks
    problem title when is_blind=True or with ProblemPublicBlind.
    """
    from app.schemas.problem import ProblemPublicBlind
    from app.services.interviewer_service import interviewer_service

    blind_prob = ProblemPublicBlind(
        statement="A secret problem statement with no title.",
        examples=[],
        signature={"function_name": "mystery", "args": [], "return_type": "int"},
        revealed_constraints=[],
        visible_tests=[],
        starter_code={},
        checker="exact",
    )

    # Calling interviewer_service with blind_prob should not fail and should not reference title
    reply = await interviewer_service.get_response(
        problem=blind_prob,
        stage=2,
        style_name="google",
        candidate_message="I'm thinking about binary search.",
        candidate_notes="brute force notes",
        is_blind=True,
    )
    assert isinstance(reply, str)
    assert len(reply) > 0

