from datetime import datetime, timezone
import json
from typing import Any, Dict
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utcnow():
    return datetime.now(timezone.utc)


class ProblemModel(Base):
    __tablename__ = "problems"

    id = Column(String(64), primary_key=True)
    title = Column(String(255), nullable=False)
    fingerprint = Column(String(128), index=True, nullable=True)
    category = Column(String(64), index=True, nullable=False)
    difficulty = Column(String(32), index=True, nullable=False)
    public_data = Column(Text, nullable=False)  # JSON string of ProblemPublic
    private_data = Column(Text, nullable=False)  # JSON string of ProblemPrivate
    created_at = Column(DateTime, default=utcnow)


class SessionModel(Base):
    __tablename__ = "sessions"

    id = Column(String(64), primary_key=True)
    problem_id = Column(String(64), ForeignKey("problems.id"), nullable=True)
    status = Column(String(32), nullable=False, default="generating")
    stage = Column(Integer, nullable=False, default=1)
    
    # Timing fields (wall-clock based)
    started_at = Column(DateTime, nullable=True)
    last_resumed_at = Column(DateTime, nullable=True)
    active_ms_accumulated = Column(Integer, default=0)
    finished_at = Column(DateTime, nullable=True)

    # Config dimensions
    source = Column(String(32), default="random_dsa")
    mode = Column(String(32), default="standard")
    style = Column(String(32), default="general")
    difficulty = Column(String(32), default="medium")
    category = Column(String(64), default="arrays_hashing")
    language = Column(String(32), default="python")
    framing = Column(String(32), default="standard")
    duration = Column(Integer, default=1200)

    # Current state
    code = Column(Text, default="")
    created_at = Column(DateTime, default=utcnow)

    problem = relationship("ProblemModel")
    stage_events = relationship("StageEventModel", back_populates="session", cascade="all, delete-orphan")
    notes = relationship("NotesModel", back_populates="session", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessageModel", back_populates="session", cascade="all, delete-orphan")
    run_results = relationship("RunResultModel", back_populates="session", cascade="all, delete-orphan")
    evaluation = relationship("EvaluationModel", back_populates="session", uselist=False, cascade="all, delete-orphan")


class StageEventModel(Base):
    __tablename__ = "stage_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), ForeignKey("sessions.id"), index=True, nullable=False)
    stage = Column(Integer, nullable=False)
    event_type = Column(String(32), nullable=False)  # "entered", "exited", "forced_advance"
    timestamp = Column(DateTime, default=utcnow)
    active_ms = Column(Integer, default=0)

    session = relationship("SessionModel", back_populates="stage_events")


class NotesModel(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), ForeignKey("sessions.id"), index=True, nullable=False)
    stage = Column(Integer, nullable=False)
    content = Column(Text, default="")
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    session = relationship("SessionModel", back_populates="notes")


class ChatMessageModel(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), ForeignKey("sessions.id"), index=True, nullable=False)
    sender = Column(String(32), nullable=False)  # "interviewer", "candidate", "system"
    stage = Column(Integer, nullable=False)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=utcnow)

    session = relationship("SessionModel", back_populates="chat_messages")


class RunResultModel(Base):
    __tablename__ = "run_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), ForeignKey("sessions.id"), index=True, nullable=False)
    is_submit = Column(Boolean, default=False)
    status = Column(String(32), nullable=False)
    passed_count = Column(Integer, default=0)
    total_count = Column(Integer, default=0)
    details = Column(Text, default="{}")  # JSON results
    timestamp = Column(DateTime, default=utcnow)

    session = relationship("SessionModel", back_populates="run_results")


class EvaluationModel(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), ForeignKey("sessions.id"), unique=True, index=True, nullable=False)
    total_score = Column(Float, nullable=False)
    verdict = Column(String(32), nullable=False)
    coding_score = Column(Float, default=0.0)
    time_mgmt_score = Column(Float, default=0.0)
    report_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    session = relationship("SessionModel", back_populates="evaluation")
