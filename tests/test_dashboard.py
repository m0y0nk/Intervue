"""
Phase 6 — Dashboard, analytics, stats SQL, revision candidates.
All assertions are deterministic (pure SQL/Python); Gemini is mocked.
"""

import json
import os
import sys
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.main import app
from app.database.session import Base, get_db
from app.models.database import EvaluationModel, ProblemModel, SessionModel

# ---------------------------------------------------------------------------
# DB setup — same pattern as other test files
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Helpers to seed DB
# ---------------------------------------------------------------------------

PROB_PUBLIC = json.dumps({
    "id": "p1",
    "title": "Two Sum",
    "statement": "...",
    "examples": [],
    "signature": {"function_name": "two_sum", "args": [], "return_type": "int[]"},
    "revealed_constraints": [],
    "visible_tests": [],
    "starter_code": {"python": "def two_sum(): pass"},
    "checker": "exact",
    "category": "arrays_hashing",
    "difficulty": "medium",
})
PROB_PRIVATE = json.dumps({"id": "p1", "title": "Two Sum"})


def _make_problem(prob_id: str = "p1", cat: str = "arrays_hashing"):
    db = TestingSessionLocal()
    p = ProblemModel(
        id=prob_id,
        title="Two Sum",
        fingerprint=f"fp_{prob_id}",
        category=cat,
        difficulty="medium",
        public_data=PROB_PUBLIC,
        private_data=PROB_PRIVATE,
    )
    db.add(p)
    db.commit()
    db.close()


def _make_session(
    sid: str,
    prob_id: str = None,
    cat: str = "arrays_hashing",
    total_score: float = 7.5,
    coding_score: float = 6.0,
    verdict: str = "hire",
    algo_score: float = 8.0,
    impl_score: float = 6.5,
):
    db = TestingSessionLocal()
    s = SessionModel(
        id=sid,
        problem_id=prob_id,
        status="finished",
        stage=7,
        source="random_dsa",
        mode="standard",
        style="general",
        difficulty="medium",
        category=cat,
        language="python",
        framing="standard",
        duration=1200,
        code="def two_sum(): pass",
        created_at=datetime.now(timezone.utc),
    )
    db.add(s)
    db.flush()

    report = {
        "session_id": sid,
        "total_score": total_score,
        "verdict": verdict,
        "algorithmic_score": algo_score,
        "implementation_score": impl_score,
        "dimension_scores": [
            {"name": "Problem Understanding", "score": 8.0, "is_deterministic": False, "rationale": "Good"},
            {"name": "Brute Force", "score": 7.0, "is_deterministic": False, "rationale": "OK"},
            {"name": "Optimal Approach", "score": 5.5, "is_deterministic": False, "rationale": "Weak"},
            {"name": "Coding Ability", "score": coding_score, "is_deterministic": True, "rationale": "Tests passed"},
            {"name": "Time Complexity", "score": 7.0, "is_deterministic": True, "rationale": "Analyzed"},
        ],
        "strengths": [],
        "weaknesses": [],
        "recommendations": [],
        "tests_passed": 3,
        "tests_total": 5,
        "stage_timings": {},
    }

    ev = EvaluationModel(
        session_id=sid,
        total_score=total_score,
        verdict=verdict,
        coding_score=coding_score,
        time_mgmt_score=7.0,
        report_json=json.dumps(report),
    )
    db.add(ev)
    db.commit()
    db.close()


# ===========================================================================
# Tests
# ===========================================================================


class TestDashboardEmpty:
    def test_empty_dashboard_returns_zero_counts(self):
        r = client.get("/api/dashboard")
        assert r.status_code == 200
        data = r.json()
        assert data["total_interviews"] == 0
        assert data["average_score"] == 0.0
        assert data["recent_sessions"] == []


class TestDashboardMetrics:
    def test_total_interviews_counted_correctly(self):
        _make_session("s1", total_score=9.0, verdict="strong_hire")
        _make_session("s2", total_score=7.0, verdict="hire")
        _make_session("s3", total_score=5.0, verdict="borderline")

        r = client.get("/api/dashboard")
        assert r.status_code == 200
        data = r.json()
        assert data["total_interviews"] == 3

    def test_average_score_calculation(self):
        _make_session("s1", total_score=8.0, verdict="hire")
        _make_session("s2", total_score=6.0, verdict="hire")

        r = client.get("/api/dashboard")
        data = r.json()
        assert data["average_score"] == pytest.approx(7.0, abs=0.05)

    def test_verdict_distribution(self):
        _make_session("s1", total_score=9.0, verdict="strong_hire")
        _make_session("s2", total_score=7.5, verdict="hire")
        _make_session("s3", total_score=7.0, verdict="hire")
        _make_session("s4", total_score=4.0, verdict="no_hire")

        r = client.get("/api/dashboard")
        data = r.json()
        dist = data["verdict_distribution"]
        assert dist.get("strong_hire") == 1
        assert dist.get("hire") == 2
        assert dist.get("no_hire") == 1


class TestCategoryPerformance:
    def test_category_performance_calculation(self):
        _make_session("s1", cat="arrays_hashing", total_score=8.0, verdict="hire")
        _make_session("s2", cat="arrays_hashing", total_score=6.0, verdict="hire")
        _make_session("s3", cat="dynamic_programming", total_score=5.0, verdict="borderline")

        r = client.get("/api/dashboard")
        data = r.json()
        cat_perf = data["category_performance"]
        assert "arrays_hashing" in cat_perf
        assert cat_perf["arrays_hashing"] == pytest.approx(7.0, abs=0.05)
        assert "dynamic_programming" in cat_perf
        assert cat_perf["dynamic_programming"] == pytest.approx(5.0, abs=0.05)


class TestWeaknessDimensionIdentification:
    def test_weakest_dimension_from_history(self):
        # Optimal Approach is 5.5 in every seeded session's report
        _make_session("s1", total_score=7.5, verdict="hire")
        _make_session("s2", total_score=8.0, verdict="hire")

        r = client.get("/api/dashboard")
        data = r.json()
        weakest = data["weakest_dimensions"]
        # Optimal Approach (5.5) should be among the weakest
        weakest_names = [d["name"] for d in weakest]
        assert "Optimal Approach" in weakest_names

    def test_strongest_dimension_from_history(self):
        # Problem Understanding is 8.0 in every seeded session's report
        _make_session("s1", total_score=7.5, verdict="hire")

        r = client.get("/api/dashboard")
        data = r.json()
        strongest = data["strongest_dimensions"]
        strongest_names = [d["name"] for d in strongest]
        assert "Problem Understanding" in strongest_names


class TestIdeaToCodeTrend:
    def test_trend_contains_algo_and_impl_scores(self):
        _make_session("s1", algo_score=8.0, impl_score=5.0, verdict="hire")
        _make_session("s2", algo_score=7.0, impl_score=6.5, verdict="hire")

        r = client.get("/api/dashboard")
        data = r.json()
        trend = data["idea_to_code_trend"]
        assert len(trend) == 2
        for entry in trend:
            assert "algorithmic_score" in entry
            assert "implementation_score" in entry
            assert "gap" in entry
        # Gaps should be positive (algo > impl in our seed data)
        gaps = [e["gap"] for e in trend if e["gap"] is not None]
        assert all(g > 0 for g in gaps)


class TestHistory:
    def test_history_pagination(self):
        for i in range(25):
            _make_session(f"s{i:03d}", total_score=7.0, verdict="hire")

        r = client.get("/api/history?page=1&page_size=10")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 25
        assert len(data["items"]) == 10
        assert data["total_pages"] == 3

    def test_history_page_2(self):
        for i in range(15):
            _make_session(f"s{i:03d}", total_score=7.0, verdict="hire")

        r = client.get("/api/history?page=2&page_size=10")
        data = r.json()
        assert len(data["items"]) == 5

    def test_history_contains_verdict(self):
        _make_session("sess_a", total_score=9.0, verdict="strong_hire")

        r = client.get("/api/history")
        data = r.json()
        assert data["items"][0]["verdict"] == "strong_hire"

    def test_history_empty_when_no_finished(self):
        # No sessions created
        r = client.get("/api/history")
        data = r.json()
        assert data["total"] == 0
        assert data["items"] == []


class TestRevisionCandidates:
    def test_revision_candidates_requires_problem(self):
        # Session with no problem_id
        _make_session("s_no_prob", prob_id=None, verdict="hire")

        r = client.get("/api/revision/candidates")
        assert r.status_code == 200
        data = r.json()
        # s_no_prob has no problem → not a candidate
        assert len(data) == 0

    def test_revision_candidates_returned_with_problem(self):
        _make_problem("prob1")
        _make_session("s_with_prob", prob_id="prob1", verdict="hire")

        r = client.get("/api/revision/candidates")
        data = r.json()
        assert len(data) == 1
        assert data[0]["session_id"] == "s_with_prob"
        assert data[0]["problem_title"] == "Two Sum"

    def test_revision_candidates_multiple(self):
        _make_problem("prob1")
        _make_problem("prob2", cat="dynamic_programming")
        _make_session("s1", prob_id="prob1", verdict="hire")
        _make_session("s2", prob_id="prob2", cat="dynamic_programming", verdict="borderline")

        r = client.get("/api/revision/candidates")
        data = r.json()
        assert len(data) == 2


class TestGeminiRecommendationIntegration:
    """
    Verifies that GET /api/dashboard/recommendations returns well-formed
    output even when Gemini is not configured (falls back to mock).
    """

    def test_recommendations_endpoint_shape(self):
        _make_session("s1", total_score=7.0, verdict="hire")

        r = client.get("/api/dashboard/recommendations")
        assert r.status_code == 200
        data = r.json()
        assert "recommendations" in data
        assert "narrative" in data
        assert isinstance(data["recommendations"], list)
        assert len(data["recommendations"]) >= 1

    def test_recommendations_no_history_returns_message(self):
        # Empty DB
        r = client.get("/api/dashboard/recommendations")
        assert r.status_code == 200
        data = r.json()
        assert len(data["recommendations"]) >= 1
        # Should mention completing an interview
        combined = " ".join(data["recommendations"]).lower()
        assert any(w in combined for w in ["interview", "session", "complete", "history"])
