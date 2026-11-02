from datetime import datetime, timezone
import json
from typing import Tuple
from sqlalchemy.orm import Session
from ..models.database import SessionModel, StageEventModel, utcnow

TOTAL_INTERVIEW_MS = 1_200_000  # 20 minutes
STAGE_6_FORCE_MS = 780_000      # 13 minutes into interview -> remaining <= 420_000 ms

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
    def get_remaining_ms(session: SessionModel) -> int:
        if session.status in ("ready", "generating"):
            return TOTAL_INTERVIEW_MS

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

        remaining = TOTAL_INTERVIEW_MS - accumulated
        return max(0, min(TOTAL_INTERVIEW_MS, remaining))

    @staticmethod
    def sync_and_check_limits(db: Session, session: SessionModel) -> SessionModel:
        """
        Synchronizes wall-clock timer and enforces hard rules:
        1. Auto-advance to Coding (stage 6) at 13:00 (active >= 780,000ms / remaining <= 420,000ms).
        2. Auto-terminate at 20:00 (remaining <= 0).
        """
        if session.status != "running":
            return session

        remaining = TimerService.get_remaining_ms(session)

        # Rule: At 20:00, terminate
        if remaining <= 0:
            session.status = "finished"
            session.finished_at = utcnow()
            session.active_ms_accumulated = TOTAL_INTERVIEW_MS
            db.commit()
            return session

        # Rule: At 13:00 (remaining <= 420,000ms), force advance into Coding (Stage 6)
        if remaining <= (TOTAL_INTERVIEW_MS - STAGE_6_FORCE_MS) and session.stage < 6:
            session.stage = 6
            # Record stage forced advance event
            event = StageEventModel(
                session_id=session.id,
                stage=6,
                event_type="forced_advance",
                active_ms=TOTAL_INTERVIEW_MS - remaining,
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

        remaining = TimerService.get_remaining_ms(session)
        active_ms = TOTAL_INTERVIEW_MS - remaining

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
