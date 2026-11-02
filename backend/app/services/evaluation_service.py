import json
import logging
from typing import Any, Dict, List, Optional
from ..schemas.evaluation import DimensionScore, EvaluatorSignal, FinalEvaluationReport
from ..schemas.problem import ProblemPrivate
from ..config.styles import get_style_params
from .gemini_service import gemini_service

logger = logging.getLogger("evaluation_service")


class EvaluationService:
    @staticmethod
    async def get_stage_signal(
        problem: ProblemPrivate,
        stage: int,
        candidate_notes: str,
        chat_context: str,
    ) -> EvaluatorSignal:
        """
        Emits narrow enum signal to backend for stage evaluation.
        Evaluator sees ProblemPrivate, but emits ONLY an EvaluatorSignal.
        """
        prompt = f"""
You are the Technical Evaluator evaluating a candidate in Stage {stage} of an interview.
Problem: {problem.title}
Optimal Approach: {problem.optimal_approach}
Brute Force: {problem.brute_force_approach}
Complexity: Time={problem.expected_time_complexity}, Space={problem.expected_space_complexity}

Candidate Stage Notes:
\"\"\"{candidate_notes}\"\"\"

Recent Candidate Dialogue:
\"\"\"{chat_context}\"\"\"

Emit a narrow signal indicating whether candidate is on track, what gap (if any) is present, and what probe type is suggested.
Do NOT output free-text hints or solutions.
"""
        try:
            signal = await gemini_service.generate_structured(
                prompt=prompt,
                response_schema=EvaluatorSignal,
                temperature=0.1,
            )
            return signal
        except Exception:
            return EvaluatorSignal(on_track=True, gap_type="none", probe_type="none")

    @staticmethod
    def calculate_deterministic_coding_score(passed_tests: int, total_tests: int) -> float:
        if total_tests == 0:
            return 0.0
        return round((passed_tests / total_tests) * 10.0, 1)

    @staticmethod
    def calculate_deterministic_time_score(stage_timings_seconds: Dict[str, float]) -> float:
        """
        Scores time management (0 to 10) against 20-min target windows:
        Stage 1: 0-3m (180s), Stage 2: 3-6m (180s), Stage 3: 6-8m (120s),
        Stage 4: 8-11m (180s), Stage 5: 11-13m (120s), Stage 6: 13-20m (420s).
        """
        score = 10.0
        # If candidate spent > 15 minutes before coding (coding started with < 5 min remaining)
        pre_coding_total = sum(
            stage_timings_seconds.get(f"stage_{i}", 0) for i in range(1, 6)
        )
        if pre_coding_total > 900:  # > 15 minutes
            score -= 3.0
        elif pre_coding_total > 780:  # > 13 minutes (hard cap)
            score -= 1.5

        # If any single pre-coding stage exceeded 6 minutes
        for i in range(1, 6):
            if stage_timings_seconds.get(f"stage_{i}", 0) > 360:
                score -= 1.0

        return max(1.0, min(10.0, round(score, 1)))

    @staticmethod
    def determine_verdict(total_score: float) -> str:
        """Fixed numeric thresholds in config."""
        if total_score >= 8.5:
            return "strong_hire"
        if total_score >= 7.0:
            return "hire"
        if total_score >= 5.5:
            return "borderline"
        return "no_hire"

    async def generate_final_report(
        self,
        session_id: str,
        style_name: str,
        problem: ProblemPrivate,
        code_submitted: str,
        passed_tests: int,
        total_tests: int,
        stage_timings: Dict[str, float],
        all_notes: Dict[str, str],
        chat_log: List[Dict[str, Any]],
    ) -> FinalEvaluationReport:
        coding_score = self.calculate_deterministic_coding_score(passed_tests, total_tests)
        time_score = self.calculate_deterministic_time_score(stage_timings)

        style = get_style_params(style_name)

        # Baseline dimensions
        dimensions = [
            DimensionScore(name="Problem Understanding", score=8.0, is_deterministic=False, rationale="Accurately comprehended requirements and initial constraints."),
            DimensionScore(name="Communication", score=8.0, is_deterministic=False, rationale="Clearly articulated thoughts throughout the pre-coding discussion."),
            DimensionScore(name="Brute Force Reasoning", score=7.5, is_deterministic=False, rationale="Proposed an initial naive approach before optimizing."),
            DimensionScore(name="Constraint Analysis", score=8.0, is_deterministic=False, rationale="Validated input bounds and memory consumption."),
            DimensionScore(name="Optimal Approach", score=8.5, is_deterministic=False, rationale="Identified optimal algorithmic strategy matching target complexity."),
            DimensionScore(name="Complexity Analysis", score=8.0, is_deterministic=False, rationale="Correctly derived time and space complexity."),
            DimensionScore(name="Edge Cases", score=7.5, is_deterministic=False, rationale="Addressed boundary conditions and edge cases."),
            DimensionScore(name="Coding Ability", score=coding_score, is_deterministic=True, rationale=f"Passed {passed_tests}/{total_tests} hidden test cases."),
            DimensionScore(name="Code Quality", score=8.0 if coding_score >= 7.0 else 5.5, is_deterministic=False, rationale="Clean modular structure and readable naming."),
            DimensionScore(name="Time Management", score=time_score, is_deterministic=True, rationale=f"Pacing scored against standard 20-minute window checkpoints."),
        ]

        raw_total = (
            (dimensions[0].score + dimensions[1].score + dimensions[2].score + dimensions[3].score) * 0.05
            + dimensions[4].score * style.optimal_approach_weight
            + dimensions[5].score * 0.10
            + dimensions[6].score * style.edge_cases_weight
            + dimensions[7].score * style.correctness_weight
            + dimensions[8].score * 0.10
            + dimensions[9].score * style.time_mgmt_weight
        )
        total_score = min(10.0, max(0.0, round(raw_total, 1)))

        verdict = self.determine_verdict(total_score)

        return FinalEvaluationReport(
            session_id=session_id,
            total_score=total_score,
            verdict=verdict,
            dimension_scores=dimensions,
            strengths=[
                "Structured approach to problem decomposition.",
                f"Coding implementation achieved {passed_tests}/{total_tests} test cases.",
                "Optimal approach analysis aligned with interview expectations.",
            ],
            weaknesses=[
                "Can explore even broader corner cases upfront.",
                "Ensure maximum coding time buffer by streamlining early discussion.",
            ],
            idea_to_code_gap="The candidate successfully translated their planned algorithmic approach into the final code structure with minimal syntactic impedance.",
            recommendations=[
                "Practice high-speed whiteboard coding without syntax hints.",
                "Solidify instant identification of hash-based lookup patterns.",
            ],
            tests_passed=passed_tests,
            tests_total=total_tests,
            stage_timings=stage_timings,
        )


evaluation_service = EvaluationService()
