import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from ..database.session import get_db
from ..models.database import (
    ChatMessageModel,
    EvaluationModel,
    NotesModel,
    ProblemModel,
    RunResultModel,
    SessionModel,
    StageEventModel,
    utcnow,
)
from ..schemas.evaluation import FinalEvaluationReport
from ..schemas.problem import (
    ProblemPrivate,
    ProblemPublic,
    ProblemPublicBlind,
    generate_starter_templates,
)
from ..schemas.session import (
    CodeUpdateRequest,
    InterviewConfig,
    NotesUpdateRequest,
    RunCodeResponse,
    SessionCreateRequest,
    SessionState,
    SubmitResponse,
)
from ..services.code_execution_service import code_execution_service
from ..services.config_validator import ConfigValidationError, validate_interview_config
from ..services.evaluation_service import evaluation_service
from ..services.problem_generator import problem_generator
from ..services.timer_service import STAGE_NAMES, TimerService

logger = logging.getLogger("api.sessions")
router = APIRouter(prefix="/api/sessions", tags=["sessions"])

# Rate limit tracking for Run Code (1 per 5s per session)
_last_run_timestamps: Dict[str, float] = {}


def _build_public_problem(
    problem_model: ProblemModel, stage: int, mode: str = "standard"
) -> Union[ProblemPublic, ProblemPublicBlind]:
    priv = ProblemPrivate.model_validate(json.loads(problem_model.private_data))

    # In stages 1-2, revealed_constraints are empty.
    # From Stage 3 onwards, constraints are revealed!
    constraints_to_show = priv.revealed_constraints if stage >= 3 else []

    # Ensure all language starter templates are present
    starter_templates = generate_starter_templates(priv.signature)
    starter_templates.update(priv.starter_code or {})
    priv.starter_code = starter_templates

    if mode == "blind_mock":
        return ProblemPublicBlind(
            statement=priv.statement,
            examples=priv.examples,
            signature=priv.signature,
            revealed_constraints=constraints_to_show,
            visible_tests=priv.visible_tests,
            starter_code=priv.starter_code,
            checker=priv.checker,
        )

    return ProblemPublic(
        id=priv.id,
        title=priv.title,
        statement=priv.statement,
        examples=priv.examples,
        signature=priv.signature,
        revealed_constraints=constraints_to_show,
        visible_tests=priv.visible_tests,
        starter_code=priv.starter_code,
        checker=priv.checker,
        category=priv.category,
        difficulty=priv.difficulty,
    )


def _serialize_session_state(db: Session, session: SessionModel) -> SessionState:
    session = TimerService.sync_and_check_limits(db, session)
    remaining_ms = TimerService.get_remaining_ms(session)

    # Fetch notes map
    notes_rows = db.query(NotesModel).filter(NotesModel.session_id == session.id).all()
    notes_dict = {str(n.stage): n.content for n in notes_rows}

    # Fetch public problem if available
    public_problem = None
    if session.problem:
        public_problem = _build_public_problem(session.problem, session.stage, session.mode)

    if session.mode == "blind_mock":
        # Server-side redaction: conceal difficulty and category from candidate state
        config = InterviewConfig(
            source=session.source,
            mode=session.mode,
            style=session.style,
            difficulty=None,
            category=None,
            language=session.language,
            framing=session.framing,
            duration=session.duration,
        )
    else:
        config = InterviewConfig(
            source=session.source,
            mode=session.mode,
            style=session.style,
            difficulty=session.difficulty,
            category=session.category,
            language=session.language,
            framing=session.framing,
            duration=session.duration,
        )

    started_at_str = session.started_at.isoformat() if session.started_at else None
    resumed_at_str = session.last_resumed_at.isoformat() if session.last_resumed_at else None

    return SessionState(
        id=session.id,
        status=session.status,
        stage=session.stage,
        stage_name=STAGE_NAMES.get(session.stage, "Unknown"),
        active_ms_accumulated=session.active_ms_accumulated or 0,
        remaining_ms=remaining_ms,
        started_at=started_at_str,
        last_resumed_at=resumed_at_str,
        config=config,
        problem=public_problem,
        notes=notes_dict,
        code=(
            session.code
            if (session.code and session.code.strip())
            else (
                public_problem.starter_code.get(session.language, "")
                if public_problem
                else ""
            )
        ),
        language=session.language,
    )


async def _async_generate_and_attach_problem(session_id: str):
    """Background task to generate problem, validate it, and mark session ready."""
    from ..database.session import SessionLocal
    db = SessionLocal()
    try:
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            return

        cfg = InterviewConfig(
            source=session.source,
            mode=session.mode,
            style=session.style,
            difficulty=session.difficulty,
            category=session.category,
            language=session.language,
            framing=session.framing,
            duration=session.duration,
        )

        problem_priv = await problem_generator.generate_problem(cfg)

        # Ensure starter templates for all languages are present
        starter_templates = generate_starter_templates(problem_priv.signature)
        starter_templates.update(problem_priv.starter_code or {})
        problem_priv.starter_code = starter_templates

        # Store in database
        problem_model = ProblemModel(
            id=problem_priv.id,
            title=problem_priv.title,
            fingerprint=problem_priv.fingerprint,
            category=problem_priv.category or cfg.category,
            difficulty=problem_priv.difficulty or cfg.difficulty,
            public_data=json.dumps(problem_priv.model_dump(exclude={"python_reference", "python_brute_force", "hidden_tests", "rubric"})),
            private_data=json.dumps(problem_priv.model_dump()),
        )
        db.merge(problem_model)

        session.problem_id = problem_model.id
        session.status = "ready"
        session.code = starter_templates.get(session.language, "")
        db.commit()
        logger.info(f"Session {session_id} prepared with problem {problem_model.title}")

    except Exception as e:
        logger.exception(f"Failed to generate problem for session {session_id}")
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if session:
            session.status = "abandoned"
            db.commit()
    finally:
        db.close()


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_session(
    req: SessionCreateRequest,
    db: Session = Depends(get_db),
):
    cfg = req.config

    # Validate configuration against Section 2 compatibility matrix
    try:
        validate_interview_config(cfg, db)
    except ConfigValidationError as err:
        raise HTTPException(status_code=422, detail=err.message)

    session_id = f"sess_{uuid.uuid4().hex[:12]}"

    new_session = SessionModel(
        id=session_id,
        status="generating",
        stage=1,
        source=cfg.source,
        mode=cfg.mode,
        style=cfg.style,
        difficulty=cfg.difficulty,
        category=cfg.category,
        language=cfg.language,
        framing=cfg.framing,
        duration=cfg.duration,
    )
    db.add(new_session)
    db.commit()

    # Trigger async generation
    asyncio.create_task(_async_generate_and_attach_problem(session_id))

    return {"session_id": session_id, "status": "generating"}


@router.get("/{session_id}", response_model=SessionState)
def get_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return _serialize_session_state(db, session)


@router.post("/{session_id}/begin", response_model=SessionState)
def begin_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status not in ("ready", "generating"):
        return _serialize_session_state(db, session)
    if session.status == "generating":
        raise HTTPException(status_code=400, detail="Problem is still generating. Please wait.")

    session = TimerService.begin(db, session)
    return _serialize_session_state(db, session)


@router.post("/{session_id}/pause", response_model=SessionState)
def pause_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session = TimerService.pause(db, session)
    return _serialize_session_state(db, session)


@router.post("/{session_id}/resume", response_model=SessionState)
def resume_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session = TimerService.resume(db, session)
    return _serialize_session_state(db, session)


@router.post("/{session_id}/reset")
def reset_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    TimerService.reset(db, session)
    return {"status": "abandoned", "session_id": session_id}


@router.post("/{session_id}/end", response_model=SessionState)
def end_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.status = "finished"
    session.finished_at = utcnow()
    db.commit()
    return _serialize_session_state(db, session)


@router.post("/{session_id}/stage/next", response_model=SessionState)
def next_stage(session_id: str, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    success, msg = TimerService.advance_stage(db, session)
    if not success:
        raise HTTPException(status_code=400, detail=msg)

    return _serialize_session_state(db, session)


@router.put("/{session_id}/notes")
def update_notes(session_id: str, req: NotesUpdateRequest, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    note = (
        db.query(NotesModel)
        .filter(NotesModel.session_id == session_id, NotesModel.stage == req.stage)
        .first()
    )
    if note:
        note.content = req.content
        note.updated_at = utcnow()
    else:
        note = NotesModel(
            session_id=session_id,
            stage=req.stage,
            content=req.content,
        )
        db.add(note)
    db.commit()
    return {"status": "saved", "stage": req.stage}


@router.put("/{session_id}/code")
def update_code(session_id: str, req: CodeUpdateRequest, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.code = req.code
    db.commit()
    return {"status": "saved"}


@router.post("/{session_id}/run", response_model=RunCodeResponse)
async def run_code(session_id: str, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.problem:
        raise HTTPException(status_code=400, detail="No problem attached to session")

    # Rate limiting: 1 run per 5s
    now_ts = time.time()
    last_run = _last_run_timestamps.get(session_id, 0.0)
    if now_ts - last_run < 5.0:
        wait_left = 5.0 - (now_ts - last_run)
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Please wait {wait_left:.1f}s before running code again.",
        )
    _last_run_timestamps[session_id] = now_ts

    problem_priv = ProblemPrivate.model_validate(json.loads(session.problem.private_data))

    # Run visible tests ONLY
    visible_tests = [
        {"args": t.args, "expected": t.expected} for t in problem_priv.visible_tests
    ]
    fn_name = problem_priv.signature.function_name

    run_res = await code_execution_service.execute(
        code=session.code or "",
        function_name=fn_name,
        tests=visible_tests,
        language=session.language,
        checker=problem_priv.checker,
        timeout_seconds=5.0,
    )

    # Save run record
    passed_cnt = sum(1 for r in run_res.results if r.passed)
    total_cnt = len(run_res.results)
    db.add(
        RunResultModel(
            session_id=session.id,
            is_submit=False,
            status=run_res.status,
            passed_count=passed_cnt,
            total_count=total_cnt,
            details=json.dumps(run_res.model_dump()),
        )
    )
    db.commit()

    return run_res


@router.post("/{session_id}/submit", response_model=SubmitResponse)
async def submit_solution(session_id: str, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.problem:
        raise HTTPException(status_code=400, detail="No problem attached to session")

    problem_priv = ProblemPrivate.model_validate(json.loads(session.problem.private_data))

    # Submit runs HIDDEN tests once
    hidden_tests = [
        {"args": t.args, "expected": t.expected} for t in problem_priv.hidden_tests
    ]
    fn_name = problem_priv.signature.function_name

    run_res = await code_execution_service.execute(
        code=session.code or "",
        function_name=fn_name,
        tests=hidden_tests,
        language=session.language,
        checker=problem_priv.checker,
        timeout_seconds=5.0,
    )

    passed_cnt = sum(1 for r in run_res.results if r.passed)
    total_cnt = len(hidden_tests)
    coding_score = evaluation_service.calculate_deterministic_coding_score(passed_cnt, total_cnt)

    failure_cat = None
    if not run_res.all_passed:
        if run_res.status == "timeout":
            failure_cat = "tle"
        elif run_res.status in ("runtime_error", "memory_limit"):
            failure_cat = "runtime_error"
        elif run_res.status == "compilation_error":
            failure_cat = "compile_error"
        else:
            failure_cat = "wrong_answer"

    # Mark session finished
    session.status = "finished"
    session.finished_at = utcnow()
    db.commit()

    # Compile stage timings
    events = (
        db.query(StageEventModel)
        .filter(StageEventModel.session_id == session.id)
        .order_by(StageEventModel.timestamp.asc())
        .all()
    )
    stage_timings: Dict[str, float] = {}
    for i in range(1, 7):
        stage_events = [e for e in events if e.stage == i]
        stage_timings[f"stage_{i}"] = 180.0 if not stage_events else float(stage_events[-1].active_ms) / 1000.0

    # Notes & chat
    notes_rows = db.query(NotesModel).filter(NotesModel.session_id == session.id).all()
    notes_dict = {str(n.stage): n.content for n in notes_rows}
    chat_rows = db.query(ChatMessageModel).filter(ChatMessageModel.session_id == session.id).all()
    chat_log = [{"sender": c.sender, "message": c.message, "stage": c.stage} for c in chat_rows]

    # Generate final report
    report = await evaluation_service.generate_final_report(
        session_id=session.id,
        style_name=session.style,
        problem=problem_priv,
        code_submitted=session.code or "",
        passed_tests=passed_cnt,
        total_tests=total_cnt,
        stage_timings=stage_timings,
        all_notes=notes_dict,
        chat_log=chat_log,
    )

    eval_model = EvaluationModel(
        session_id=session.id,
        total_score=report.total_score,
        verdict=report.verdict,
        coding_score=coding_score,
        time_mgmt_score=evaluation_service.calculate_deterministic_time_score(stage_timings),
        report_json=json.dumps(report.model_dump()),
    )
    db.merge(eval_model)
    db.commit()

    return SubmitResponse(
        status="completed",
        passed_count=passed_cnt,
        total_count=total_cnt,
        failure_category=failure_cat,
        coding_score=coding_score,
        finished_at=session.finished_at.isoformat(),
    )


@router.get("/{session_id}/report", response_model=FinalEvaluationReport)
def get_report(session_id: str, db: Session = Depends(get_db)):
    evaluation = (
        db.query(EvaluationModel)
        .filter(EvaluationModel.session_id == session_id)
        .first()
    )
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation report not found")
    return FinalEvaluationReport.model_validate(json.loads(evaluation.report_json))
