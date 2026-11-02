from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class EvaluatorSignal(BaseModel):
    on_track: bool = True
    gap_type: Literal[
        "none",
        "misread_problem",
        "missing_bruteforce",
        "wrong_complexity",
        "missed_constraint",
        "wrong_approach",
        "missing_edge_case",
        "unclear_communication",
    ] = "none"
    probe_type: Literal["clarify", "complexity", "correctness", "edge_case", "none"] = "none"


class DimensionScore(BaseModel):
    name: str
    score: float  # 0 to 10
    is_deterministic: bool = False
    evidence_quote: Optional[str] = None
    rationale: str = ""


class FinalEvaluationReport(BaseModel):
    session_id: str
    total_score: float  # 0 to 10
    verdict: Literal["strong_hire", "hire", "borderline", "no_hire"]
    dimension_scores: List[DimensionScore]
    strengths: List[str]
    weaknesses: List[str]
    idea_to_code_gap: str  # Narrative explaining divergence between reasoning and implementation
    recommendations: List[str]
    tests_passed: int
    tests_total: int
    stage_timings: Dict[str, float] = Field(default_factory=dict)  # stage -> active seconds
