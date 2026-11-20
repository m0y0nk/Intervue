from datetime import datetime, timezone
import json
from typing import Tuple
from sqlalchemy.orm import Session
from ..models.database import SessionModel, StageEventModel, utcnow

TOTAL_INTERVIEW_MS = 1_200_000  # Default 20 minutes fallback
STAGE_6_FORCE_MS = 780_000      # 13 minutes default pre-coding limit

STAGE_NAMES = {
    1: "Understanding",
    2: "Brute force",
    3: "Constraint analysis",
    4: "Optimal approach",
    5: "Edge cases",
    6: "Coding",
}


class TimerService:
    @staticmethod
    def get_total_duration_ms(session: SessionModel) -> int:
        return (session.duration or 1200) * 1000

    @staticmethod
    def get_remaining_ms(session: SessionModel) -> int:
        total_ms = TimerService.get_total_duration_ms(session)
        if session.status in ("ready", "generating"):
            return total_ms

        if session.status in ("finished", "abandoned"):
            return 0

        accumulated = session.active_ms_accumulated or 0

        if session.status == "running" and session.last_resumed_at:
            now = utcnow()
            resumed_at = session.last_resumed_at
            if resumed_at.tzinfo is None:
                resumed_at = resumed_at.replace(tzinfo=timezone.utc)
            delta_ms = int((now - resumed_at).total_seconds() * 1000)
            accumulated += max(0, delta_ms)

        remaining = total_ms - accumulated
        return max(0, min(total_ms, remaining))

    @staticmethod
    def sync_and_check_limits(db: Session, session: SessionModel) -> SessionModel:
        """
        Synchronizes wall-clock timer and enforces dynamic rules:
        1. Auto-advance to Coding (stage 6) when remaining time reaches the coding budget.
        2. Auto-terminate at total duration (remaining <= 0).
        """
        if session.status != "running":
            return session

        total_ms = TimerService.get_total_duration_ms(session)
        remaining = TimerService.get_remaining_ms(session)

        # Rule: When total time expires, terminate
        if remaining <= 0:
            session.status = "finished"
            session.finished_at = utcnow()
            session.active_ms_accumulated = total_ms
            db.commit()
            return session

        # Rule: Force advance into Coding (Stage 6) when pre-coding budget expires
        coding_ms = 420_000  # Default 7 mins (for 20 min interview)
        if session.stage_time_budgets:
            try:
                budgets = json.loads(session.stage_time_budgets)
                if isinstance(budgets, dict) and "coding" in budgets and budgets["coding"] > 0:
                    coding_ms = int(budgets["coding"] * 60 * 1000)
            except Exception:
                pass
        else:
            # By default reserve at least 35% of total time for coding
            coding_ms = max(300_000, int(total_ms * 0.35))

        if remaining <= coding_ms and session.stage < 6:
            session.stage = 6
            # Record stage forced advance event
            event = StageEventModel(
                session_id=session.id,
                stage=6,
                event_type="forced_advance",
                active_ms=total_ms - remaining,
            )
            db.add(event)
            db.commit()

        return session

    @staticmethod
    def begin(db: Session, session: SessionModel) -> SessionModel:
        if session.status not in ("ready", "generating"):
            return session

        now = utcnow()
        session.status = "running"
        session.started_at = now
        session.last_resumed_at = now
        session.active_ms_accumulated = 0
        session.stage = 1

        event = StageEventModel(
            session_id=session.id,
            stage=1,
            event_type="entered",
            active_ms=0,
        )
        db.add(event)
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def pause(db: Session, session: SessionModel) -> SessionModel:
        if session.status != "running":
            return session

        now = utcnow()
        resumed_at = session.last_resumed_at
        if resumed_at:
            if resumed_at.tzinfo is None:
                resumed_at = resumed_at.replace(tzinfo=timezone.utc)
            delta_ms = int((now - resumed_at).total_seconds() * 1000)
            session.active_ms_accumulated += max(0, delta_ms)

        session.status = "paused"
        session.last_resumed_at = None
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def resume(db: Session, session: SessionModel) -> SessionModel:
        if session.status != "paused":
            return session

        session.status = "running"
        session.last_resumed_at = utcnow()
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def reset(db: Session, session: SessionModel) -> None:
        """Abandons current session."""
        session.status = "abandoned"
        session.finished_at = utcnow()
        db.commit()

    @staticmethod
    def advance_stage(db: Session, session: SessionModel) -> Tuple[bool, str]:
        TimerService.sync_and_check_limits(db, session)

        if session.status != "running":
            return False, f"Cannot advance stage while session is {session.status}"

        if session.stage >= 6:
            return False, "Already in final Coding stage. Use Submit to complete interview."

        curr_stage = session.stage
        next_stage = curr_stage + 1
        session.stage = next_stage

        total_ms = TimerService.get_total_duration_ms(session)
        remaining = TimerService.get_remaining_ms(session)
        active_ms = total_ms - remaining

        # Record stage transition event
        db.add(
            StageEventModel(
                session_id=session.id,
                stage=curr_stage,
                event_type="exited",
                active_ms=active_ms,
            )
        )
        db.add(
            StageEventModel(
                session_id=session.id,
                stage=next_stage,
                event_type="entered",
                active_ms=active_ms,
            )
        )

        db.commit()
        db.refresh(session)
        return True, f"Advanced to stage {next_stage}: {STAGE_NAMES.get(next_stage)}"
