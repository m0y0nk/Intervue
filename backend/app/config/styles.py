from typing import Dict, Literal
from pydantic import BaseModel


class StyleParams(BaseModel):
    max_follow_ups_per_stage: int
    tone: str
    rubric_focus: str
    optimal_approach_weight: float
    edge_cases_weight: float
    correctness_weight: float
    communication_weight: float
    time_mgmt_weight: float


STYLE_CONFIGS: Dict[str, StyleParams] = {
    "google": StyleParams(
        max_follow_ups_per_stage=3,
        tone="probing, terse",
        rubric_focus="higher on optimal approach and complexity",
        optimal_approach_weight=0.25,
        edge_cases_weight=0.15,
        correctness_weight=0.20,
        communication_weight=0.20,
        time_mgmt_weight=0.20,
    ),
    "amazon": StyleParams(
        max_follow_ups_per_stage=2,
        tone="structured, ownership-minded",
        rubric_focus="higher on edge cases and code quality",
        optimal_approach_weight=0.15,
        edge_cases_weight=0.25,
        correctness_weight=0.25,
        communication_weight=0.20,
        time_mgmt_weight=0.15,
    ),
    "meta": StyleParams(
        max_follow_ups_per_stage=2,
        tone="fast, product-minded",
        rubric_focus="higher on coding speed and correctness",
        optimal_approach_weight=0.15,
        edge_cases_weight=0.15,
        correctness_weight=0.35,
        communication_weight=0.15,
        time_mgmt_weight=0.20,
    ),
    "general": StyleParams(
        max_follow_ups_per_stage=2,
        tone="neutral",
        rubric_focus="balanced",
        optimal_approach_weight=0.20,
        edge_cases_weight=0.20,
        correctness_weight=0.20,
        communication_weight=0.20,
        time_mgmt_weight=0.20,
    ),
}


def get_style_params(style_name: str) -> StyleParams:
    return STYLE_CONFIGS.get(style_name.lower(), STYLE_CONFIGS["general"])
