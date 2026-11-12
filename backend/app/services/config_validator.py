"""
Configuration Compatibility Engine for Intervue.
Validates InterviewConfig dimensions (Source, Mode, Style, Difficulty, Category, Framing, Language)
against the compatibility matrix defined in Section 2 of SPEC.md.
"""

from typing import List
from sqlalchemy.orm import Session
from ..models.database import SessionModel
from ..schemas.session import InterviewConfig


class ConfigValidationError(Exception):
    """Raised when an interview configuration violates compatibility rules."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def validate_interview_config(cfg: InterviewConfig, db: Session) -> None:
    """
    Enforces compatibility validation per Section 2 of SPEC.md:
    - duration: fixed 20 minutes (1200s), not configurable.
    - topic_mastery with category = mixed: invalid (requires category != mixed).
    - revision with no prior attempts: invalid.
    - revision with source/category not matching a prior completed problem: invalid.
    - adaptive source with fewer than 5 completed interviews and fewer than 2 in any category:
      reject and tell user to use Random Practice or pick a topic. Never fabricate history.
    - adaptive difficulty: only allowed when source is adaptive.
    - framing == business: only allowed for random_dsa and leetcode.
    - blind_mock: allowed with any source or mode (topic_mastery + blind_mock allowed).
    """

    # 1. Fixed duration constraint (SPEC line 49)
    if cfg.duration != 1200:
        raise ConfigValidationError("Duration is fixed at 20 minutes (1200 seconds) and cannot be configured.")

    # 2. Topic mastery constraint (SPEC line 60)
    if cfg.mode == "topic_mastery":
        if cfg.category == "mixed":
            raise ConfigValidationError("Topic mastery mode requires a specific category and cannot be used with 'mixed'.")

    # 3. Framing constraint (SPEC line 48)
    if cfg.framing == "business":
        if cfg.source == "ai_business":
            # ai_business source is inherently business-framed; normalize framing to standard
            cfg.framing = "standard"
        elif cfg.source not in ("random_dsa", "leetcode"):
            raise ConfigValidationError("Business framing is only supported for sources 'random_dsa' and 'leetcode'.")

    # 4. Adaptive difficulty constraint (SPEC line 43)
    if cfg.difficulty == "adaptive" and cfg.source != "adaptive":
        raise ConfigValidationError("Adaptive difficulty is only supported when source is 'adaptive'.")

    # Query completed sessions from database for history-dependent validations
    completed_sessions: List[SessionModel] = (
        db.query(SessionModel)
        .filter(SessionModel.status == "finished")
        .all()
    )

    # 5. Revision mode constraints (SPEC lines 57, 61, 62)
    if cfg.mode == "revision":
        if not completed_sessions:
            raise ConfigValidationError(
                "Revision mode requires at least one prior completed interview attempt."
            )

        # Check if an eligible past problem exists
        eligible = False
        for s in completed_sessions:
            if s.problem_id:
                if cfg.category == "mixed" or s.category == cfg.category:
                    eligible = True
                    break

        if not eligible:
            raise ConfigValidationError(
                f"No eligible revision problems found for category '{cfg.category}'."
            )

    # 6. Adaptive source cold-start rejection (SPEC lines 63, 124)
    if cfg.source == "adaptive":
        total_completed = len(completed_sessions)
        category_counts = {}
        for s in completed_sessions:
            category_counts[s.category] = category_counts.get(s.category, 0) + 1

        max_in_any_cat = max(category_counts.values()) if category_counts else 0

        if total_completed < 5 or max_in_any_cat < 2:
            raise ConfigValidationError(
                "Adaptive practice requires at least 5 completed interviews and at least 2 in a single category. "
                "Please use Random Practice or Topic Mastery to build history first."
            )

