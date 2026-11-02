from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.models.database import Base, SessionModel
from app.services.timer_service import (
    STAGE_6_FORCE_MS,
    TOTAL_INTERVIEW_MS,
    TimerService,
    utcnow,
)


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.close()


def test_timer_initial_and_begin(test_db):
    session = SessionModel(
        id="s1",
        status="ready",
        stage=1,
    )
    test_db.add(session)
    test_db.commit()

    assert TimerService.get_remaining_ms(session) == TOTAL_INTERVIEW_MS

    # Begin
    session = TimerService.begin(test_db, session)
    assert session.status == "running"
    assert session.started_at is not None
    assert session.last_resumed_at is not None
    rem = TimerService.get_remaining_ms(session)
    assert 1_199_000 <= rem <= TOTAL_INTERVIEW_MS


def test_timer_pause_and_resume(test_db):
    now = utcnow()
    session = SessionModel(
        id="s2",
        status="running",
        stage=1,
        started_at=now - timedelta(seconds=60),
        last_resumed_at=now - timedelta(seconds=60),
        active_ms_accumulated=0,
    )
    test_db.add(session)
    test_db.commit()

    # Remaining should be ~ 1,200,000 - 60,000 = 1,140,000
    rem = TimerService.get_remaining_ms(session)
    assert 1_139_000 <= rem <= 1_141_000

    # Pause
    session = TimerService.pause(test_db, session)
    assert session.status == "paused"
    assert 59_000 <= session.active_ms_accumulated <= 61_000

    # Resume after a while
    session = TimerService.resume(test_db, session)
    assert session.status == "running"
    rem_after_resume = TimerService.get_remaining_ms(session)
    assert 1_138_000 <= rem_after_resume <= 1_141_000


def test_timer_auto_advance_to_stage_6_at_13_mins(test_db):
    now = utcnow()
    # 13 minutes and 10 seconds elapsed (790 seconds = 790,000 ms)
    session = SessionModel(
        id="s3",
        status="running",
        stage=2,
        started_at=now - timedelta(seconds=790),
        last_resumed_at=now - timedelta(seconds=790),
        active_ms_accumulated=0,
    )
    test_db.add(session)
    test_db.commit()

    session = TimerService.sync_and_check_limits(test_db, session)
    # Must be forced into Stage 6 (Coding)
    assert session.stage == 6


def test_timer_auto_terminate_at_20_mins(test_db):
    now = utcnow()
    # 20 minutes and 5 seconds elapsed
    session = SessionModel(
        id="s4",
        status="running",
        stage=6,
        started_at=now - timedelta(seconds=1205),
        last_resumed_at=now - timedelta(seconds=1205),
        active_ms_accumulated=0,
    )
    test_db.add(session)
    test_db.commit()

    session = TimerService.sync_and_check_limits(test_db, session)
    # Must be marked finished
    assert session.status == "finished"
    assert TimerService.get_remaining_ms(session) == 0
