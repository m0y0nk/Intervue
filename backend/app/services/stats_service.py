"""
Pure deterministic SQL/Python stats service.
No Gemini calls here — only aggregation over stored records.
"""

import json
from collections import defaultdict
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ..models.database import EvaluationModel, SessionModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_avg(values: List[float]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0


def _verdict_color(verdict: str) -> str:
    return {
        "strong_hire": "emerald",
        "hire": "green",
        "borderline": "amber",
        "no_hire": "red",
    }.get(verdict, "zinc")


# ---------------------------------------------------------------------------
# Main aggregation
# ---------------------------------------------------------------------------


def compute_dashboard_stats(db: Session) -> Dict[str, Any]:
    """
    Deterministically compute all dashboard metrics from stored DB records.
    Returns a dict of pre-computed numbers; no LLM involved.
    """
    finished = (
        db.query(SessionModel)
        .filter(SessionModel.status == "finished")
        .order_by(SessionModel.created_at.desc())
        .all()
    )

    total_interviews = len(finished)

    if total_interviews == 0:
        return _empty_stats()

    # Map session_id -> evaluation
    evals = db.query(EvaluationModel).all()
    eval_map: Dict[str, EvaluationModel] = {e.session_id: e for e in evals}

    # -----------------------------------------------------------------------
    # Per-session accumulators
    # -----------------------------------------------------------------------
    scores: List[float] = []
    coding_scores: List[float] = []
    algo_scores: List[float] = []
    impl_scores: List[float] = []
    time_scores: List[float] = []

    # dimension name -> list of scores across all sessions
    dimension_accumulator: Dict[str, List[float]] = defaultdict(list)

    # category -> list of total scores
    category_scores: Dict[str, List[float]] = defaultdict(list)

    # verdict tallies
    verdict_counts: Dict[str, int] = defaultdict(int)

    # Idea-to-Code trend (chronological, oldest first)
    idea_to_code_trend: List[Dict[str, Any]] = []

    recent_sessions: List[Dict[str, Any]] = []

    for s in finished:
        ev: Optional[EvaluationModel] = eval_map.get(s.id)
        total_sc = ev.total_score if ev else 0.0
        code_sc = ev.coding_score if ev else 0.0

        scores.append(total_sc)
        coding_scores.append(code_sc)

        # Parse report JSON for dimension-level data
        algo_sc: Optional[float] = None
        impl_sc: Optional[float] = None
        if ev and ev.report_json:
            try:
                report = json.loads(ev.report_json)
                a = report.get("algorithmic_score")
                i = report.get("implementation_score")
                if a is not None:
                    algo_sc = float(a)
                    algo_scores.append(algo_sc)
                if i is not None:
                    impl_sc = float(i)
                    impl_scores.append(impl_sc)

                # Accumulate dimension scores
                for dim in report.get("dimension_scores", []):
                    dim_name = dim.get("name", "")
                    dim_score = dim.get("score")
                    if dim_name and dim_score is not None:
                        dimension_accumulator[dim_name].append(float(dim_score))
            except (json.JSONDecodeError, TypeError, ValueError):
                pass

        time_sc = ev.time_mgmt_score if ev else 0.0
        time_scores.append(time_sc)

        cat = s.category or "mixed"
        category_scores[cat].append(total_sc)

        verdict = ev.verdict if ev else "no_hire"
        verdict_counts[verdict] += 1

        # Idea-to-Code trend entry
        idea_to_code_trend.append(
            {
                "session_id": s.id,
                "date": s.created_at.isoformat() if s.created_at else None,
                "algorithmic_score": algo_sc,
                "implementation_score": impl_sc,
                "gap": (
                    round(algo_sc - impl_sc, 2)
                    if algo_sc is not None and impl_sc is not None
                    else None
                ),
            }
        )

        # Recent sessions list (top 10 by recency)
        recent_sessions.append(
            {
                "session_id": s.id,
                "problem_title": (
                    s.problem.title if s.problem else "Coding Interview"
                ),
                "category": s.category,
                "difficulty": s.difficulty,
                "style": s.style,
                "mode": s.mode,
                "language": s.language,
                "score": total_sc,
                "verdict": verdict,
                "verdict_color": _verdict_color(verdict),
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
        )

    # -----------------------------------------------------------------------
    # Aggregated metrics
    # -----------------------------------------------------------------------
    avg_score = _safe_avg(scores)
    avg_coding = _safe_avg(coding_scores)
    avg_algo = _safe_avg(algo_scores)
    avg_impl = _safe_avg(impl_scores)
    avg_time = _safe_avg(time_scores)

    # Per-category averages
    category_performance: Dict[str, float] = {
        cat: _safe_avg(vals) for cat, vals in category_scores.items()
    }

    # Dimension ranking
    dimension_averages = {
        name: _safe_avg(vals)
        for name, vals in dimension_accumulator.items()
    }
    sorted_dims = sorted(
        dimension_averages.items(), key=lambda x: x[1], reverse=True
    )
    strongest_dimensions = [{"name": n, "avg_score": s} for n, s in sorted_dims[:3]]
    weakest_dimensions = [{"name": n, "avg_score": s} for n, s in sorted_dims[-3:]]

    # Reverse trend to chronological order
    idea_to_code_trend.reverse()

    return {
        "total_interviews": total_interviews,
        "average_score": avg_score,
        "coding_accuracy": avg_coding,
        "average_algorithmic_score": avg_algo,
        "average_implementation_score": avg_impl,
        "average_time_mgmt_score": avg_time,
        "category_performance": category_performance,
        "strongest_dimensions": strongest_dimensions,
        "weakest_dimensions": weakest_dimensions,
        "verdict_distribution": dict(verdict_counts),
        "idea_to_code_trend": idea_to_code_trend,
        "recent_sessions": recent_sessions[:10],
    }


def _empty_stats() -> Dict[str, Any]:
    return {
        "total_interviews": 0,
        "average_score": 0.0,
        "coding_accuracy": 0.0,
        "average_algorithmic_score": 0.0,
        "average_implementation_score": 0.0,
        "average_time_mgmt_score": 0.0,
        "category_performance": {},
        "strongest_dimensions": [],
        "weakest_dimensions": [],
        "verdict_distribution": {},
        "idea_to_code_trend": [],
        "recent_sessions": [],
    }


# ---------------------------------------------------------------------------
# History query
# ---------------------------------------------------------------------------


def get_session_history(
    db: Session, page: int = 1, page_size: int = 20
) -> Dict[str, Any]:
    """Paginated list of all finished sessions."""
    total = (
        db.query(SessionModel)
        .filter(SessionModel.status == "finished")
        .count()
    )

    rows = (
        db.query(SessionModel)
        .filter(SessionModel.status == "finished")
        .order_by(SessionModel.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    evals = db.query(EvaluationModel).all()
    eval_map = {e.session_id: e for e in evals}

    items = []
    for s in rows:
        ev = eval_map.get(s.id)
        items.append(
            {
                "session_id": s.id,
                "problem_title": (
                    s.problem.title if s.problem else "Coding Interview"
                ),
                "category": s.category,
                "difficulty": s.difficulty,
                "style": s.style,
                "mode": s.mode,
                "language": s.language,
                "source": s.source,
                "score": ev.total_score if ev else None,
                "verdict": ev.verdict if ev else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
        )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total else 0,
        "items": items,
    }


# ---------------------------------------------------------------------------
# Revision candidates
# ---------------------------------------------------------------------------


def get_revision_candidates(db: Session) -> List[Dict[str, Any]]:
    """
    Returns finished sessions that have a valid linked problem —
    these are eligible for revision mode.
    """
    rows = (
        db.query(SessionModel)
        .filter(
            SessionModel.status == "finished",
            SessionModel.problem_id.isnot(None),
        )
        .order_by(SessionModel.created_at.desc())
        .all()
    )

    evals = db.query(EvaluationModel).all()
    eval_map = {e.session_id: e for e in evals}

    candidates = []
    for s in rows:
        if not s.problem:
            continue
        ev = eval_map.get(s.id)
        candidates.append(
            {
                "session_id": s.id,
                "problem_id": s.problem_id,
                "problem_title": s.problem.title,
                "category": s.category,
                "difficulty": s.difficulty,
                "source": s.source,
                "score": ev.total_score if ev else None,
                "verdict": ev.verdict if ev else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
        )

    return candidates

