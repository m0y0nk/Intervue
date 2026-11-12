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
    score: float = Field(ge=0.0, le=10.0)  # 0 to 10
    is_deterministic: bool = False
    evidence_quote: Optional[str] = None
    rationale: str = ""


class RevisionComparison(BaseModel):
    prior_session_id: str
    prior_date: Optional[str] = None
    prior_score: float
    current_score: float
    score_delta: float
    prior_verdict: str
    current_verdict: str
    prior_tests_passed: int
    current_tests_passed: int
    tests_total: int
    dimension_deltas: Dict[str, float] = Field(default_factory=dict)
    summary: str


class LLMEvaluatedDimension(BaseModel):
    name: str
    score: float = Field(ge=0.0, le=10.0, description="Anchored score 0 to 10 based on rubric scale")
    evidence_quote: str = Field(default="", description="Direct quote from candidate notes or chat")
    rationale: str = Field(description="Rubric-grounded justification for this score")


class LLMFinalEvaluation(BaseModel):
    dimensions: List[LLMEvaluatedDimension]
    strengths: List[str]
    weaknesses: List[str]
    idea_to_code_gap_explanation: str
    recommendations: List[str]


class FinalEvaluationReport(BaseModel):
    session_id: str
    total_score: float  # 0 to 10
    verdict: Literal["strong_hire", "hire", "borderline", "no_hire"]
    dimension_scores: List[DimensionScore]
    strengths: List[str]
    weaknesses: List[str]
    idea_to_code_gap: str  # Narrative explaining divergence between reasoning and implementation
    algorithmic_score: Optional[float] = None
    implementation_score: Optional[float] = None
    recommendations: List[str]
    tests_passed: int
    tests_total: int
    stage_timings: Dict[str, float] = Field(default_factory=dict)  # stage -> active seconds
    revision_comparison: Optional[RevisionComparison] = None
