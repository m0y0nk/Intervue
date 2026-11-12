import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database.session import get_db
from ..models.database import EvaluationModel, SessionModel
from ..services.gemini_service import gemini_service
from ..services.stats_service import (
    compute_dashboard_stats,
    get_revision_candidates,
    get_session_history,
)

logger = logging.getLogger("dashboard")

router = APIRouter(tags=["dashboard"])


# ---------------------------------------------------------------------------
# GET /api/dashboard
# ---------------------------------------------------------------------------


@router.get("/api/dashboard")
def get_dashboard(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Returns all deterministic dashboard statistics.
    Optionally appends a Gemini-written interpretation narrative
    (Gemini never derives the numbers — only writes prose about them).
    """
    stats = compute_dashboard_stats(db)
    return stats


# ---------------------------------------------------------------------------
# GET /api/dashboard/recommendations
# ---------------------------------------------------------------------------


@router.get("/api/dashboard/recommendations")
async def get_recommendations(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Calls Gemini with pre-computed stats and returns a text narrative.
    Gemini receives only the aggregated numbers — never raw DB rows.
    """
    stats = compute_dashboard_stats(db)

    if stats["total_interviews"] == 0:
        return {
            "recommendations": [
                "Complete at least one interview to receive personalised recommendations."
            ],
            "narrative": "No interview history found. Start a session to get insights.",
        }

    # Build a compact summary dict for Gemini (numbers only, no raw data)
    summary = {
        "total_interviews": stats["total_interviews"],
        "average_score": stats["average_score"],
        "coding_accuracy": stats["coding_accuracy"],
        "average_algorithmic_score": stats["average_algorithmic_score"],
        "average_implementation_score": stats["average_implementation_score"],
        "strongest_dimensions": stats["strongest_dimensions"],
        "weakest_dimensions": stats["weakest_dimensions"],
        "verdict_distribution": stats["verdict_distribution"],
        "category_performance": stats["category_performance"],
    }

    prompt = f"""You are a senior engineering interview coach reviewing a candidate's interview history dashboard.

Here are the candidate's computed performance statistics:
{json.dumps(summary, indent=2)}

Write a concise, honest, anti-slop coaching analysis (3-5 bullet points) covering:
1. What the candidate is genuinely doing well
2. The single biggest gap they must close to get hired
3. One specific, actionable drill or technique they should practice this week
4. Category or dimension they should focus on next

Be direct, specific, and encouraging. No filler phrases.
Return a JSON object: {{"recommendations": ["...", "...", "..."], "narrative": "2-3 sentence summary"}}"""

    try:
        from pydantic import BaseModel

        class RecommendationResponse(BaseModel):
            recommendations: List[str]
            narrative: str

        result = await gemini_service.generate_structured(
            prompt=prompt,
            response_schema=RecommendationResponse,
            temperature=0.4,
        )
        return result.model_dump()
    except Exception as e:
        logger.warning(f"Gemini recommendations failed: {e}")
        return {
            "recommendations": [
                f"Average score {stats['average_score']}/10 — keep practising.",
                "Focus on your weakest dimensions.",
                "Aim for 3 interviews per week to build consistency.",
            ],
            "narrative": "Personalised recommendations temporarily unavailable.",
        }


# ---------------------------------------------------------------------------
# GET /api/history
# ---------------------------------------------------------------------------


@router.get("/api/history")
def get_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Paginated list of all finished sessions."""
    return get_session_history(db, page=page, page_size=page_size)


# ---------------------------------------------------------------------------
# GET /api/revision/candidates
# ---------------------------------------------------------------------------


@router.get("/api/revision/candidates")
def list_revision_candidates(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Sessions eligible for revision mode (finished, with a linked problem)."""
    return get_revision_candidates(db)
