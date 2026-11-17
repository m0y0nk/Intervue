import logging
from fastapi import APIRouter, HTTPException, Path
from ..services.leetcode_service import leetcode_service

logger = logging.getLogger("api.leetcode")
router = APIRouter(prefix="/api/leetcode", tags=["leetcode"])


@router.get("/problem/{problem_id_or_slug}")
async def get_leetcode_problem(
    problem_id_or_slug: str = Path(..., description="Problem number (e.g. 1, 42) or title slug (e.g. two-sum)")
):
    """
    Queries LeetCode public GraphQL API for problem details using problem number or slug.
    """
    clean_query = problem_id_or_slug.strip()
    if not clean_query:
        raise HTTPException(status_code=400, detail="Problem ID or slug cannot be empty.")

    problem = await leetcode_service.fetch_problem(clean_query)
    if not problem:
        raise HTTPException(
            status_code=404,
            detail=f"LeetCode problem '{clean_query}' not found. Please verify the problem number or slug.",
        )

    return problem
