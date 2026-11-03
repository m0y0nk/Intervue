from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field
from .problem import ProblemPublic, ProblemPublicBlind


class InterviewConfig(BaseModel):
    source: Literal["ai_business", "leetcode", "random_dsa", "adaptive", "custom"] = "random_dsa"
    mode: Literal["standard", "blind_mock", "topic_mastery", "revision"] = "standard"
    style: Literal["google", "amazon", "meta", "general"] = "general"
    difficulty: Optional[Literal["easy", "medium", "hard", "adaptive"]] = "medium"
    category: Optional[Literal[
        "arrays_hashing",
        "two_pointers",
        "sliding_window",
        "binary_search",
        "stack_queue",
        "linked_lists",
        "trees",
        "graphs",
        "dynamic_programming",
        "greedy",
        "backtracking",
        "heaps",
        "intervals",
        "mixed",
    ]] = "arrays_hashing"
    language: Literal["python", "java", "cpp"] = "python"
    framing: Literal["standard", "business"] = "standard"
    duration: int = 1200  # fixed 20 minutes (1200 s), not configurable


class SessionCreateRequest(BaseModel):
    config: InterviewConfig = Field(default_factory=InterviewConfig)


class SessionState(BaseModel):
    id: str
    status: Literal["generating", "ready", "running", "paused", "finished", "abandoned"]
    stage: int  # 1 to 6
    stage_name: str
    active_ms_accumulated: int
    remaining_ms: int
    started_at: Optional[str] = None
    last_resumed_at: Optional[str] = None
    config: InterviewConfig
    problem: Optional[Union[ProblemPublic, ProblemPublicBlind]] = None
    notes: Dict[str, str] = Field(default_factory=dict)  # stage index -> notes text
    code: str = ""
    language: str = "python"


class NotesUpdateRequest(BaseModel):
    stage: int
    content: str


class CodeUpdateRequest(BaseModel):
    code: str
    language: Optional[str] = "python"


class ChatMessageSchema(BaseModel):
    id: Optional[str] = None
    sender: Literal["interviewer", "candidate", "system"]
    message: str
    stage: int
    timestamp: str


class InterviewerChatRequest(BaseModel):
    message: str


class InterviewerChatResponse(BaseModel):
    message: str
    stage: int


class RunTestResultItem(BaseModel):
    passed: bool
    input: List[Any]
    expected: Any
    actual: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None


class RunCodeResponse(BaseModel):
    status: str
    all_passed: bool
    results: List[RunTestResultItem]
    stdout: str = ""
    stderr: str = ""
    compile_error: Optional[str] = None
    error: Optional[str] = None


class SubmitResponse(BaseModel):
    status: str
    passed_count: int
    total_count: int
    failure_category: Optional[str] = None  # None, "wrong_answer", "tle", "runtime_error", "compile_error"
    coding_score: float  # 0 to 10
    finished_at: str
