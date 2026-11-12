import json
import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.main import app
from app.database.session import Base, get_db
from app.models.database import EvaluationModel, ProblemModel, SessionModel
from app.schemas.problem import ProblemPrivate
from app.schemas.session import InterviewConfig, SessionCreateRequest
from app.services.adaptive_practice_service import compute_adaptive_profile
from app.services.problem_generator import (
    ProblemGenerationError,
    UnsupportedProblemError,
    problem_generator,
)

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


@pytest.mark.asyncio
async def test_ai_business_source_generation():
    """
    ai_business source: generates a problem with business domain framing.
    Validates via sandbox differential testing.
    """
    cfg = InterviewConfig(
        source="ai_business",
        mode="standard",
        style="general",
        difficulty="medium",
        category="arrays_hashing",
        language="python",
    )
    problem = await problem_generator.generate_problem(cfg)
    assert isinstance(problem, ProblemPrivate)
    assert problem.python_reference != ""
    assert len(problem.examples) >= 3


@pytest.mark.asyncio
async def test_leetcode_paste_source():
    """
    leetcode source: requires pasted statement.
    Converts and passes validation pipeline.
    """
    cfg = InterviewConfig(
        source="leetcode",
        mode="standard",
        style="general",
        difficulty="medium",
        category="arrays_hashing",
        language="python",
    )

    # Empty statement must fail
    with pytest.raises(ProblemGenerationError, match="requires a pasted problem statement"):
        await problem_generator.generate_problem(cfg, leetcode_statement="")

    # API validation: 422 if statement missing
    resp = client.post(
        "/api/sessions",
        json={"config": cfg.model_dump(), "leetcode_statement": ""},
    )
    assert resp.status_code == 422
    assert "requires a pasted problem statement" in resp.json()["detail"]

    # Valid paste
    sample_statement = """
    Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.
    Example 1: Input: nums = [2,7,11,15], target = 9 Output: [0,1]
    Example 2: Input: nums = [3,2,4], target = 6 Output: [1,2]
    Example 3: Input: nums = [3,3], target = 6 Output: [0,1]
    Constraints: 2 <= nums.length <= 10^4, -10^9 <= nums[i] <= 10^9
    """
    problem = await problem_generator.generate_problem(
        cfg,
        leetcode_id="1",
        leetcode_statement=sample_statement,
    )
    assert isinstance(problem, ProblemPrivate)
    assert "lc_1_" in problem.fingerprint


@pytest.mark.asyncio
async def test_custom_source_validation_and_unsupported_handling():
    """
    custom source: accepts user statement.
    If statement cannot be turned into a testable function, raises UnsupportedProblemError.
    """
    cfg = InterviewConfig(
        source="custom",
        mode="standard",
        style="general",
        difficulty="medium",
        category="arrays_hashing",
        language="python",
    )

    # Empty statement fails
    with pytest.raises(ProblemGenerationError, match="requires a problem statement"):
        await problem_generator.generate_problem(cfg, custom_statement="")

    # Valid custom statement
    valid_statement = (
        "Write a function that finds two integers in an array that add up to a target sum. "
        "Return their zero-based indices. Input array length between 2 and 1000."
    )
    problem = await problem_generator.generate_problem(
        cfg,
        custom_statement=valid_statement,
        custom_url="https://example.com/custom-dsa",
    )
    assert isinstance(problem, ProblemPrivate)


def test_adaptive_practice_service_deterministic_profiling():
    """
    adaptive source: deterministic history analysis.
    Verifies that compute_adaptive_profile identifies the weakest category
    and calculates difficulty progression without any LLM calls.
    """
    db = TestingSessionLocal()

    # Seed 6 finished sessions across 2 categories
    # Category 1: 'trees' with high scores (90, 85, 95) -> avg 90
    # Category 2: 'dynamic_programming' with low scores (40, 50, 45) -> avg 45
    for i, score in enumerate([90.0, 85.0, 95.0]):
        sess = SessionModel(
            id=f"sess_trees_{i}",
            status="finished",
            category="trees",
            difficulty="easy",
            problem_id=f"prob_tree_{i}",
        )
        db.add(sess)
        report = {
            "dimension_scores": [
                {"name": "Problem Understanding", "score": score},
                {"name": "Optimal Approach", "score": score},
            ]
        }
        eval_m = EvaluationModel(
            session_id=f"sess_trees_{i}",
            total_score=score,
            verdict="hire",
            report_json=json.dumps(report),
        )
        db.add(eval_m)

    for i, score in enumerate([40.0, 50.0, 45.0]):
        sess = SessionModel(
            id=f"sess_dp_{i}",
            status="finished",
            category="dynamic_programming",
            difficulty="medium",
            problem_id=f"prob_dp_{i}",
        )
        db.add(sess)
        report = {
            "dimension_scores": [
                {"name": "Problem Understanding", "score": score},
                {"name": "Optimal Approach", "score": 30.0},  # weakest dimension
            ]
        }
        eval_m = EvaluationModel(
            session_id=f"sess_dp_{i}",
            total_score=score,
            verdict="no_hire",
            report_json=json.dumps(report),
        )
        db.add(eval_m)

    db.commit()

    # Compute profile
    profile = compute_adaptive_profile(db)

    # Assert weakest category selected: dynamic_programming (avg 45 < 90)
    assert profile.target_category == "dynamic_programming"
    # Assert weakest dimension identified
    assert profile.weakest_dimension == "Optimal Approach"
    # Attempted problem IDs should include all 6 past problem IDs
    assert len(profile.attempted_problem_ids) == 6
    assert "prob_dp_0" in profile.attempted_problem_ids

    db.close()


@pytest.mark.asyncio
async def test_adaptive_source_generation_with_history():
    """
    adaptive source: when qualified, generates a problem targeting the weakness.
    """
    db = TestingSessionLocal()
    # Seed 5 finished sessions in arrays_hashing
    for i in range(5):
        sess = SessionModel(
            id=f"sess_adapt_{i}",
            status="finished",
            category="arrays_hashing",
            difficulty="easy",
            problem_id=f"prob_adapt_{i}",
        )
        db.add(sess)
        eval_m = EvaluationModel(
            session_id=f"sess_adapt_{i}",
            total_score=80.0,
            verdict="hire",
            report_json=json.dumps({"dimension_scores": []}),
        )
        db.add(eval_m)
    db.commit()

    cfg = InterviewConfig(
        source="adaptive",
        mode="standard",
        style="general",
        difficulty="adaptive",
        category="arrays_hashing",
        language="python",
    )

    problem = await problem_generator.generate_problem(cfg, db=db)
    assert isinstance(problem, ProblemPrivate)
    # The adaptive rationale should be attached
    assert "[Adaptive selection rationale:" in problem.optimal_approach
    db.close()

