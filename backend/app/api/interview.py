import json
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database.session import get_db
from ..models.database import ChatMessageModel, NotesModel, ProblemModel, SessionModel
from ..schemas.problem import ProblemPrivate, ProblemPublic, ProblemPublicBlind
from ..schemas.session import (
    ChatMessageSchema,
    InterviewerChatRequest,
    InterviewerChatResponse,
)
from ..services.evaluation_service import evaluation_service
from ..services.interviewer_service import interviewer_service
from ..services.timer_service import TimerService

logger = logging.getLogger("api.interview")
router = APIRouter(prefix="/api/sessions", tags=["interview"])


@router.get("/{session_id}/chat", response_model=List[ChatMessageSchema])
def get_chat_history(session_id: str, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = (
        db.query(ChatMessageModel)
        .filter(ChatMessageModel.session_id == session_id)
        .order_by(ChatMessageModel.timestamp.asc())
        .all()
    )
    return [
        ChatMessageSchema(
            id=str(m.id),
            sender=m.sender,
            message=m.message,
            stage=m.stage,
            timestamp=m.timestamp.isoformat(),
        )
        for m in messages
    ]


@router.post("/{session_id}/interviewer", response_model=InterviewerChatResponse)
async def chat_with_interviewer(
    session_id: str,
    req: InterviewerChatRequest,
    db: Session = Depends(get_db),
):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    TimerService.sync_and_check_limits(db, session)

    if session.status != "running":
        raise HTTPException(
            status_code=400,
            detail=f"Interview session is {session.status}. Please start or resume it.",
        )

    # CRITICAL RULE: Zero LLM calls in Coding stage (stage 6) -> 409 Conflict
    if session.stage >= 6:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The interviewer is not active during the Coding stage. Focus on your implementation.",
        )

    if not session.problem:
        raise HTTPException(status_code=400, detail="Problem not attached to session")

    # Record candidate message
    candidate_msg = ChatMessageModel(
        session_id=session.id,
        sender="candidate",
        stage=session.stage,
        message=req.message,
    )
    db.add(candidate_msg)
    db.commit()

    # Retrieve candidate notes for current stage
    note_row = (
        db.query(NotesModel)
        .filter(NotesModel.session_id == session.id, NotesModel.stage == session.stage)
        .first()
    )
    candidate_notes = note_row.content if note_row else ""

    # Parse problem
    problem_priv = ProblemPrivate.model_validate(json.loads(session.problem.private_data))

    # Build public problem for interviewer (respecting blind mock redaction)
    if session.mode == "blind_mock":
        problem_pub = ProblemPublicBlind(
            statement=problem_priv.statement,
            examples=problem_priv.examples,
            signature=problem_priv.signature,
            revealed_constraints=problem_priv.revealed_constraints if session.stage >= 3 else [],
            visible_tests=problem_priv.visible_tests,
            starter_code=problem_priv.starter_code or {},
            checker=problem_priv.checker,
        )
    else:
        problem_pub = ProblemPublic(
            id=problem_priv.id,
            title=problem_priv.title,
            statement=problem_priv.statement,
            examples=problem_priv.examples,
            signature=problem_priv.signature,
            revealed_constraints=problem_priv.revealed_constraints if session.stage >= 3 else [],
            visible_tests=problem_priv.visible_tests,
            starter_code=problem_priv.starter_code or {},
            checker=problem_priv.checker,
            category=problem_priv.category,
            difficulty=problem_priv.difficulty,
        )

    # Evaluator generates narrow signal
    signal = await evaluation_service.get_stage_signal(
        problem=problem_priv,
        stage=session.stage,
        candidate_notes=candidate_notes,
        chat_context=req.message,
    )

    # Interviewer generates response with public problem only
    interviewer_reply = await interviewer_service.get_response(
        problem=problem_pub,
        stage=session.stage,
        style_name=session.style,
        candidate_message=req.message,
        candidate_notes=candidate_notes,
        evaluator_signal=signal,
        is_blind=(session.mode == "blind_mock"),
    )

    # Record interviewer reply
    bot_msg = ChatMessageModel(
        session_id=session.id,
        sender="interviewer",
        stage=session.stage,
        message=interviewer_reply,
    )
    db.add(bot_msg)
    db.commit()

    return InterviewerChatResponse(
        message=interviewer_reply,
        stage=session.stage,
    )
