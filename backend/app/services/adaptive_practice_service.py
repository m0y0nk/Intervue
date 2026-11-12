"""
Adaptive Practice Service for Intervue.

Computes weaknesses from stored evaluation history using deterministic SQL/Python.
Maps weakness profile → category / difficulty selection for next problem.

Rules (Section 4 of SPEC.md):
- Use only real stored scores. Never invent history.
- Cold-start guard enforced upstream by config_validator.py (>= 5 sessions, >= 2 in any category).
- Selection priority: lowest per-category avg → weakest dimension across all sessions → avoid repeats.
- Difficulty progression: if last N sessions in a category all scored > 75%, step up difficulty.
"""

import json
import logging
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from ..models.database import EvaluationModel, ProblemModel, SessionModel

logger = logging.getLogger("adaptive_practice_service")

DIFFICULTY_ORDER = ["easy", "medium", "hard"]

# Dimensions tracked in DimensionScore
TRACKED_DIMENSIONS = [
    "Problem Understanding",
    "Brute Force",
    "Constraint Analysis",
    "Optimal Approach",
    "Edge Cases",
    "Code Quality",
]


class AdaptiveProfile:
    """Summary of weakness analysis from stored history."""

    def __init__(
        self,
        target_category: str,
        target_difficulty: str,
        weakest_dimension: Optional[str],
        rationale: str,
        attempted_problem_ids: List[str],
    ):
        self.target_category = target_category
        self.target_difficulty = target_difficulty
        self.weakest_dimension = weakest_dimension
        self.rationale = rationale
        self.attempted_problem_ids = attempted_problem_ids


def compute_adaptive_profile(db: Session) -> AdaptiveProfile:
    """
    Pure deterministic computation — no Gemini calls.
    Returns an AdaptiveProfile specifying what to generate next.
    """
    finished_sessions: List[SessionModel] = (
        db.query(SessionModel)
        .filter(SessionModel.status == "finished")
        .all()
    )

    session_ids = [s.id for s in finished_sessions]

    # Fetch all evaluations
    evaluations: List[EvaluationModel] = (
        db.query(EvaluationModel)
        .filter(EvaluationModel.session_id.in_(session_ids))
        .all()
    )

    eval_map: Dict[str, EvaluationModel] = {e.session_id: e for e in evaluations}

    # Per-category stats
    category_scores: Dict[str, List[float]] = {}
    # Per-session problem ids for dedup
    attempted_problem_ids: List[str] = []

    for s in finished_sessions:
        if s.problem_id:
            attempted_problem_ids.append(s.problem_id)
        if s.id in eval_map:
            cat = s.category or "mixed"
            score = eval_map[s.id].total_score
            category_scores.setdefault(cat, []).append(score)

    # Compute per-category averages
    category_avg: Dict[str, float] = {
        cat: sum(scores) / len(scores)
        for cat, scores in category_scores.items()
        if len(scores) >= 1
    }

    # Pick weakest category (min average, at least 1 session)
    if category_avg:
        target_category = min(category_avg, key=lambda c: category_avg[c])
        logger.info(
            f"Adaptive: weakest category = {target_category} "
            f"(avg={category_avg[target_category]:.1f})"
        )
    else:
        target_category = "arrays_hashing"

    # Compute difficulty progression for that category
    cat_sessions = [
        s for s in finished_sessions if (s.category or "mixed") == target_category
    ]
    cat_session_ids = [s.id for s in cat_sessions]
    recent_cat_scores = [
        eval_map[sid].total_score
        for sid in cat_session_ids[-5:]  # last 5 in category
        if sid in eval_map
    ]

    # Current difficulty in category (take most frequent from last sessions)
    recent_difficulties = [
        s.difficulty for s in cat_sessions[-5:] if s.difficulty in DIFFICULTY_ORDER
    ]
    current_difficulty = (
        max(set(recent_difficulties), key=recent_difficulties.count)
        if recent_difficulties
        else "easy"
    )

    # Step up if doing well (all recent >= 75)
    if recent_cat_scores and all(sc >= 75 for sc in recent_cat_scores):
        current_idx = DIFFICULTY_ORDER.index(current_difficulty) if current_difficulty in DIFFICULTY_ORDER else 0
        next_idx = min(current_idx + 1, len(DIFFICULTY_ORDER) - 1)
        target_difficulty = DIFFICULTY_ORDER[next_idx]
        logger.info(
            f"Adaptive: stepping up difficulty {current_difficulty} → {target_difficulty}"
        )
    else:
        target_difficulty = current_difficulty

    # Find weakest dimension across all sessions
    dimension_totals: Dict[str, List[float]] = {}
    for eval_model in evaluations:
        try:
            report = json.loads(eval_model.report_json)
            for dim in report.get("dimension_scores", []):
                name = dim.get("name", "")
                score = dim.get("score", 0)
                if name in TRACKED_DIMENSIONS:
                    dimension_totals.setdefault(name, []).append(score)
        except Exception:
            pass

    weakest_dimension = None
    if dimension_totals:
        dim_avgs = {
            name: sum(scores) / len(scores)
            for name, scores in dimension_totals.items()
        }
        weakest_dimension = min(dim_avgs, key=lambda d: dim_avgs[d])
        logger.info(
            f"Adaptive: weakest dimension = {weakest_dimension} "
            f"(avg={dim_avgs[weakest_dimension]:.1f})"
        )

    rationale = (
        f"History analysis: weakest category is '{target_category}' "
        f"(avg score {category_avg.get(target_category, 0):.0f}/100). "
        f"Target difficulty: {target_difficulty}."
        + (f" Weakest dimension: {weakest_dimension}." if weakest_dimension else "")
    )

    return AdaptiveProfile(
        target_category=target_category,
        target_difficulty=target_difficulty,
        weakest_dimension=weakest_dimension,
        rationale=rationale,
        attempted_problem_ids=list(set(attempted_problem_ids)),
    )


adaptive_practice_service = type(
    "AdaptivePracticeService",
    (),
    {"compute_profile": staticmethod(compute_adaptive_profile)},
)()

