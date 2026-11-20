import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.database.session import Base
from app.models.database import ProblemModel, SessionModel, utcnow
from app.schemas.problem import ProblemPrivate
from app.services.gemini_service import gemini_service
from app.services.timer_service import TimerService
from app.services.evaluation_service import evaluation_service

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def test_problem_schema_contains_dynamic_time_budgets():
    """Verify that ProblemPrivate defines time_limit_minutes and stage_time_budgets."""
    prob = gemini_service._mock_response("two_sum", ProblemPrivate)
    assert prob.time_limit_minutes in (15, 20, 22, 25, 30)
    assert isinstance(prob.stage_time_budgets, dict)
    assert "understanding" in prob.stage_time_budgets
    assert "coding" in prob.stage_time_budgets
    assert prob.stage_time_budgets["coding"] >= 5


def test_timer_service_dynamic_duration():
    """Verify TimerService respects dynamic session.duration instead of fixed 20m."""
    db = TestingSessionLocal()
    # 30-minute Hard problem session (1800s)
    sess_hard = SessionModel(
        id="sess_hard_30m",
        status="running",
        stage=1,
        started_at=utcnow(),
        last_resumed_at=utcnow(),
        duration=1800,
        active_ms_accumulated=0,
        stage_time_budgets=json.dumps({
            "understanding": 4,
            "brute_force": 4,
            "constraints": 2,
            "optimal": 5,
            "edge_cases": 3,
            "coding": 12,
        }),
    )
    db.add(sess_hard)
    db.commit()

    total_ms = TimerService.get_total_duration_ms(sess_hard)
    assert total_ms == 1_800_000  # 30 minutes in ms

    remaining = TimerService.get_remaining_ms(sess_hard)
    assert 1_790_000 <= remaining <= 1_800_000

    # 15-minute Easy problem session (900s)
    sess_easy = SessionModel(
        id="sess_easy_15m",
        status="ready",
        stage=1,
        duration=900,
        stage_time_budgets=json.dumps({
            "understanding": 2,
            "brute_force": 2,
            "constraints": 1,
            "optimal": 2,
            "edge_cases": 2,
            "coding": 6,
        }),
    )
    db.add(sess_easy)
    db.commit()

    assert TimerService.get_total_duration_ms(sess_easy) == 900_000
    assert TimerService.get_remaining_ms(sess_easy) == 900_000
    db.close()


def test_dynamic_force_advance_to_coding():
    """Verify force-advance into Stage 6 (Coding) triggers when pre-coding budget expires."""
    db = TestingSessionLocal()
    # 30-minute session with 12m (720s) coding budget -> pre-coding budget is 18m (1080s)
    # When remaining <= 12m (720,000ms), stage must auto-advance to 6
    sess = SessionModel(
        id="sess_test_force",
        status="running",
        stage=3,  # Candidate still in constraints stage
        duration=1800,
        active_ms_accumulated=1_100_000,  # 18.3 minutes spent (> 18m pre-coding)
        last_resumed_at=utcnow(),
        stage_time_budgets=json.dumps({
            "understanding": 4,
            "brute_force": 4,
            "constraints": 2,
            "optimal": 5,
            "edge_cases": 3,
            "coding": 12,
        }),
    )
    db.add(sess)
    db.commit()

    TimerService.sync_and_check_limits(db, sess)
    assert sess.stage == 6, "Should force advance to Stage 6 (Coding) once pre-coding time is exhausted"
    db.close()


def test_evaluation_dynamic_time_scoring():
    """Verify evaluation service scores time management scaled to dynamic duration."""
    # 30-minute problem (1800s) with 12m coding (720s) -> pre-coding budget = 1080s
    timings_30m = {
        "stage_1": 200.0,
        "stage_2": 200.0,
        "stage_3": 150.0,
        "stage_4": 300.0,
        "stage_5": 150.0,
        "stage_6": 700.0,
    }
    # Pre-coding total = 1000s <= 1080s target -> ideal score
    score = evaluation_service.calculate_deterministic_time_score(
        timings_30m,
        total_duration_seconds=1800.0,
        coding_budget_seconds=720.0,
    )
    assert score == 10.0

    # If candidate spent too long in pre-coding (e.g. 1300s > 1080s)
    slow_timings_30m = {
        "stage_1": 300.0,
        "stage_2": 300.0,
        "stage_3": 200.0,
        "stage_4": 400.0,
        "stage_5": 150.0,
    }
    score_slow = evaluation_service.calculate_deterministic_time_score(
        slow_timings_30m,
        total_duration_seconds=1800.0,
        coding_budget_seconds=720.0,
    )
    assert score_slow < 10.0
