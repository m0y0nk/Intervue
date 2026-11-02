import json
from typing import Any, Dict, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database.session import get_db
from ..models.database import EvaluationModel, SessionModel

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def get_dashboard_metrics(db: Session = Depends(get_db)):
    """Computes deterministic dashboard statistics strictly from stored records."""
    sessions = (
        db.query(SessionModel)
        .filter(SessionModel.status == "finished")
        .order_by(SessionModel.created_at.desc())
        .all()
    )

    total_interviews = len(sessions)
    if total_interviews == 0:
        return {
            "total_interviews": 0,
            "average_score": 0.0,
            "coding_accuracy": 0.0,
            "category_performance": {},
            "recent_sessions": [],
        }

    evals = db.query(EvaluationModel).all()
    eval_map = {e.session_id: e for e in evals}

    scores = []
    coding_scores = []
    category_scores: Dict[str, List[float]] = {}
    recent = []

    for s in sessions:
        ev = eval_map.get(s.id)
        sc = ev.total_score if ev else 0.0
        cs = ev.coding_score if ev else 0.0
        scores.append(sc)
        coding_scores.append(cs)

        cat = s.category or "mixed"
        category_scores.setdefault(cat, []).append(sc)

        recent.append(
            {
                "session_id": s.id,
                "problem_title": s.problem.title if s.problem else "Coding Interview",
                "category": s.category,
                "difficulty": s.difficulty,
                "style": s.style,
                "score": sc,
                "verdict": ev.verdict if ev else "no_hire",
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
        )

    avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
    avg_coding = round(sum(coding_scores) / len(coding_scores), 1) if coding_scores else 0.0

    cat_perf = {
        cat: round(sum(vals) / len(vals), 1)
        for cat, vals in category_scores.items()
    }

    return {
        "total_interviews": total_interviews,
        "average_score": avg_score,
        "coding_accuracy": avg_coding,
        "category_performance": cat_perf,
        "recent_sessions": recent[:10],
    }
