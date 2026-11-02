from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FunctionArg(BaseModel):
    name: str
    type: str  # int, long, double, bool, string, int[], int[][], string[], ListNode, TreeNode


class FunctionSignature(BaseModel):
    function_name: str
    args: List[FunctionArg]
    return_type: str


class ProblemExample(BaseModel):
    input_str: str
    output_str: str
    explanation: Optional[str] = None


class TestCaseSchema(BaseModel):
    args: List[Any]
    expected: Any


class ProblemPublic(BaseModel):
    id: str
    title: str
    statement: str
    examples: List[ProblemExample]
    signature: FunctionSignature
    revealed_constraints: List[str] = Field(default_factory=list)
    visible_tests: List[TestCaseSchema] = Field(default_factory=list)
    starter_code: Dict[str, str] = Field(default_factory=dict)  # language -> template
    checker: str = Field(default="exact")  # exact | unordered | float_tolerance(eps)
    category: Optional[str] = None
    difficulty: Optional[str] = None


class ProblemPublicBlind(BaseModel):
    id: str
    statement: str
    examples: List[ProblemExample]
    signature: FunctionSignature
    revealed_constraints: List[str] = Field(default_factory=list)
    visible_tests: List[TestCaseSchema] = Field(default_factory=list)
    starter_code: Dict[str, str] = Field(default_factory=dict)
    checker: str = Field(default="exact")


class RubricItem(BaseModel):
    dimension: str
    criteria: str
    weight: float = 1.0


class ProblemPrivate(ProblemPublic):
    """
    CRITICAL ISOLATION:
    Only evaluation_service and problem_validator may import ProblemPrivate.
    Interviewer routes, interviewer service and all frontend-facing schemas
    must import ProblemPublic or ProblemPublicBlind only.
    """
    categories: List[str] = Field(default_factory=list)
    difficulty: str = "medium"
    brute_force_approach: str = ""
    optimal_approach: str = ""
    alternative_approaches: List[str] = Field(default_factory=list)
    expected_time_complexity: str = ""
    expected_space_complexity: str = ""
    python_reference: str = ""
    python_brute_force: str = ""
    input_generator: str = ""  # python snippet generating list of test args
    hidden_tests: List[TestCaseSchema] = Field(default_factory=list)
    edge_cases: List[str] = Field(default_factory=list)
    rubric: List[RubricItem] = Field(default_factory=list)
    fingerprint: Optional[str] = None
