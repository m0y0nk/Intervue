import json
import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.models.database import Base, EvaluationModel, ProblemModel, SessionModel, utcnow
from app.schemas.evaluation import EvaluatorSignal, FinalEvaluationReport
from app.schemas.problem import ProblemPrivate
from app.services.evaluation_service import evaluation_service
from app.services.gemini_service import gemini_service

TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.mark.asyncio
async def test_evaluator_stage_signal():
    """
    Evaluator agent emits a schema-limited signal:
    on_track: bool, gap_type: str, probe_type: str.
    No free text derived from the rubric or reference.
    """
    mock_prob = gemini_service._mock_response("", ProblemPrivate)

    signal = await evaluation_service.get_stage_signal(
        problem=mock_prob,
        stage=2,
        candidate_notes="Thinking of using two nested loops to check all pairs.",
        chat_context="Candidate: I will iterate through all elements.",
    )

    assert isinstance(signal, EvaluatorSignal)
    assert isinstance(signal.on_track, bool)
    assert signal.gap_type in [
        "none",
        "misread_problem",
        "missing_bruteforce",
        "wrong_complexity",
        "missed_constraint",
        "wrong_approach",
        "missing_edge_case",
        "unclear_communication",
    ]
    assert signal.probe_type in ["clarify", "complexity", "correctness", "edge_case", "none"]


def test_deterministic_coding_score():
    """
    Deterministic scoring: Coding Ability from hidden test pass rate and failure category.
    """
    # 4/4 passed -> 10.0
    assert evaluation_service.calculate_deterministic_coding_score(4, 4) == 10.0
    # 2/4 passed, wrong answer -> 5.0
    assert evaluation_service.calculate_deterministic_coding_score(2, 4, "wrong_answer") == 5.0
    # 0/4 passed -> 0.0
    assert evaluation_service.calculate_deterministic_coding_score(0, 4) == 0.0
    # Compile error penalty
    assert evaluation_service.calculate_deterministic_coding_score(0, 4, "compile_error") == 0.0
    assert evaluation_service.calculate_deterministic_coding_score(2, 4, "compile_error") <= 2.0
    # Runtime error / TLE penalty on imperfect pass
    assert evaluation_service.calculate_deterministic_coding_score(3, 4, "tle") == 6.5


def test_deterministic_time_score():
    """
    Deterministic scoring: Time Management against 20-min window checkpoints.
    Stage 1: 180s, Stage 2: 180s, Stage 3: 120s, Stage 4: 180s, Stage 5: 120s, Stage 6: 420s.
    """
    # Ideal pacing: 150s per stage 1-5 (total 750s <= 780s target)
    ideal_timings = {f"stage_{i}": 150.0 for i in range(1, 6)}
    assert evaluation_service.calculate_deterministic_time_score(ideal_timings) == 10.0

    # Mild delay (> 13 mins = 780s pre-coding)
    mild_timings = {f"stage_{i}": 165.0 for i in range(1, 6)}  # 825s
    score_mild = evaluation_service.calculate_deterministic_time_score(mild_timings)
    assert score_mild == 8.5

    # Heavy delay (> 15 mins = 900s pre-coding)
    slow_timings = {f"stage_{i}": 190.0 for i in range(1, 6)}  # 950s
    score_slow = evaluation_service.calculate_deterministic_time_score(slow_timings)
    assert score_slow <= 6.5

    # Single stage took > 6 mins (360s)
    stuck_timings = {"stage_1": 400.0, "stage_2": 60.0, "stage_3": 60.0, "stage_4": 60.0, "stage_5": 60.0}
    score_stuck = evaluation_service.calculate_deterministic_time_score(stuck_timings)
    assert score_stuck == 9.0  # 10 - 1.0


def test_fixed_verdict_thresholds():
    """
    Fixed numeric thresholds in config:
    >= 8.5 -> strong_hire
    >= 7.0 -> hire
    >= 5.5 -> borderline
    < 5.5  -> no_hire
    """
    assert evaluation_service.determine_verdict(9.2) == "strong_hire"
    assert evaluation_service.determine_verdict(8.5) == "strong_hire"
    assert evaluation_service.determine_verdict(8.4) == "hire"
    assert evaluation_service.determine_verdict(7.0) == "hire"
    assert evaluation_service.determine_verdict(6.9) == "borderline"
    assert evaluation_service.determine_verdict(5.5) == "borderline"
    assert evaluation_service.determine_verdict(5.4) == "no_hire"
    assert evaluation_service.determine_verdict(2.0) == "no_hire"


@pytest.mark.asyncio
async def test_final_evaluation_report_generation():
    """
    Full evaluation report contains:
    - 10 dimension scores (with is_deterministic flags)
    - total_score and verdict
    - Idea-to-Code Gap (algorithmic_score, implementation_score, narrative)
    - strengths, weaknesses, recommendations
    """
    mock_prob = gemini_service._mock_response("", ProblemPrivate)

    notes = {
        "1": "Array can contain positive and negative numbers. Exactly one solution.",
        "2": "Brute force: O(N^2) pairwise comparisons.",
        "3": "N <= 10^5, so O(N^2) will TLE. Target O(N).",
        "4": "Optimal: Single-pass hash map storing diff -> index.",
        "5": "Edge cases: duplicates, negative target, zero values.",
    }

    report = await evaluation_service.generate_final_report(
        session_id="test_eval_sess_01",
        style_name="google",
        problem=mock_prob,
        code_submitted="def two_sum(nums, target):\n    seen = {}\n    for i, x in enumerate(nums):\n        if target - x in seen: return [seen[target - x], i]\n        seen[x] = i\n    return []\n",
        passed_tests=4,
        total_tests=4,
        stage_timings={f"stage_{i}": 150.0 for i in range(1, 7)},
        all_notes=notes,
        chat_log=[],
    )

    assert isinstance(report, FinalEvaluationReport)
    assert len(report.dimension_scores) == 10

    dim_map = {d.name: d for d in report.dimension_scores}
    assert dim_map["Coding Ability"].is_deterministic is True
    assert dim_map["Coding Ability"].score == 10.0
    assert dim_map["Time Management"].is_deterministic is True
    assert dim_map["Time Management"].score == 10.0
    assert dim_map["Optimal Approach"].is_deterministic is False

    # Check Idea-to-Code Gap metrics
    assert report.algorithmic_score is not None
    assert report.implementation_score == 10.0
    assert len(report.idea_to_code_gap) > 20

    # Check verdict
    assert report.verdict in ["strong_hire", "hire", "borderline", "no_hire"]
    assert len(report.strengths) >= 1
    assert len(report.weaknesses) >= 1
    assert len(report.recommendations) >= 1


def test_revision_mode_comparison_calculation():
    """
    Revision comparison:
    Computes delta against prior attempt (scores, verdict, tests passed, dimension deltas).
    """
    prior_report = {
        "total_score": 6.0,
        "verdict": "borderline",
        "tests_passed": 2,
        "tests_total": 4,
        "dimension_scores": [
            {"name": "Coding Ability", "score": 5.0},
            {"name": "Optimal Approach", "score": 6.5},
            {"name": "Time Management", "score": 7.0},
        ],
    }
    prior_eval = EvaluationModel(
        session_id="prior_sess_01",
        total_score=6.0,
        verdict="borderline",
        report_json=json.dumps(prior_report),
        created_at=utcnow(),
    )

    current_dims = [
        {"name": "Coding Ability", "score": 10.0},
        {"name": "Optimal Approach", "score": 9.0},
        {"name": "Time Management", "score": 9.0},
    ]
    from app.schemas.evaluation import DimensionScore
    current_dim_objs = [
        DimensionScore(name=d["name"], score=d["score"], is_deterministic=True)
        for d in current_dims
    ]

    rev_comp = evaluation_service.compute_revision_comparison(
        current_session_id="new_sess_02",
        current_score=8.5,
        current_verdict="strong_hire",
        current_tests_passed=4,
        total_tests=4,
        current_dimensions=current_dim_objs,
        prior_evaluation=prior_eval,
    )

    assert rev_comp is not None
    assert rev_comp.prior_session_id == "prior_sess_01"
    assert rev_comp.prior_score == 6.0
    assert rev_comp.current_score == 8.5
    assert rev_comp.score_delta == 2.5
    assert rev_comp.prior_verdict == "borderline"
    assert rev_comp.current_verdict == "strong_hire"
    assert rev_comp.prior_tests_passed == 2
    assert rev_comp.current_tests_passed == 4
    # Dimension deltas
    assert rev_comp.dimension_deltas["Coding Ability"] == 5.0
    assert rev_comp.dimension_deltas["Optimal Approach"] == 2.5
    assert "improved by +2.5 points" in rev_comp.summary

