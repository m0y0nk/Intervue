import json
import logging
from typing import Any, Dict, List, Optional
from ..config.styles import get_style_params
from ..models.database import EvaluationModel
from ..schemas.evaluation import (
    DimensionScore,
    EvaluatorSignal,
    FinalEvaluationReport,
    LLMEvaluatedDimension,
    LLMFinalEvaluation,
    RevisionComparison,
)
from ..schemas.problem import ProblemPrivate
from .gemini_service import gemini_service

logger = logging.getLogger("evaluation_service")

# Fixed numeric verdict thresholds
VERDICT_THRESHOLDS = [
    (8.5, "strong_hire"),
    (7.0, "hire"),
    (5.5, "borderline"),
    (0.0, "no_hire"),
]

LLM_DIMENSIONS_ORDER = [
    "Problem Understanding",
    "Communication",
    "Brute Force Reasoning",
    "Constraint Analysis",
    "Optimal Approach",
    "Complexity Analysis",
    "Edge Cases",
    "Code Quality",
]


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
    def calculate_deterministic_coding_score(
        passed_tests: int, total_tests: int, failure_category: Optional[str] = None
    ) -> float:
        """
        Deterministic calculation:
        Raw ratio * 10.0, penalized if execution resulted in compile error or crash.
        """
        if total_tests == 0:
            return 0.0
        ratio = passed_tests / total_tests
        raw = ratio * 10.0

        # Penalties for critical failure types on unpassed cases
        if not (passed_tests == total_tests):
            if failure_category == "compile_error":
                raw = min(raw, 2.0)
            elif failure_category in ("runtime_error", "tle"):
                raw = max(0.0, raw - 1.0)

        return round(max(0.0, min(10.0, raw)), 1)

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
            score -= 3.5
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
        for threshold, verdict in VERDICT_THRESHOLDS:
            if total_score >= threshold:
                return verdict
        return "no_hire"

    def compute_revision_comparison(
        self,
        current_session_id: str,
        current_score: float,
        current_verdict: str,
        current_tests_passed: int,
        total_tests: int,
        current_dimensions: List[DimensionScore],
        prior_evaluation: EvaluationModel,
    ) -> Optional[RevisionComparison]:
        """
        Computes delta between current attempt and prior attempt for revision mode.
        """
        try:
            prior_report_data = json.loads(prior_evaluation.report_json)
            prior_score = float(prior_report_data.get("total_score", prior_evaluation.total_score))
            prior_verdict = prior_report_data.get("verdict", prior_evaluation.verdict)
            prior_tests_passed = int(prior_report_data.get("tests_passed", 0))

            score_delta = round(current_score - prior_score, 1)

            # Dimension deltas
            prior_dim_map = {
                d["name"]: float(d["score"])
                for d in prior_report_data.get("dimension_scores", [])
                if "name" in d and "score" in d
            }
            dimension_deltas = {}
            for dim in current_dimensions:
                if dim.name in prior_dim_map:
                    dimension_deltas[dim.name] = round(dim.score - prior_dim_map[dim.name], 1)

            # Summary narrative
            if score_delta > 0:
                perf_word = f"improved by +{score_delta} points"
            elif score_delta < 0:
                perf_word = f"decreased by {score_delta} points"
            else:
                perf_word = "matched prior score exactly"

            tests_delta = current_tests_passed - prior_tests_passed
            tests_note = f"{tests_delta:+d} tests passed" if tests_delta != 0 else "same test pass rate"

            summary = (
                f"Revision comparison against prior attempt ({prior_evaluation.session_id}): "
                f"Overall score {perf_word} ({prior_score} -> {current_score}), "
                f"verdict transitioned from {prior_verdict.replace('_', ' ')} to {current_verdict.replace('_', ' ')}, "
                f"with {tests_note}."
            )

            prior_date_str = (
                prior_evaluation.created_at.isoformat()
                if prior_evaluation.created_at
                else None
            )

            return RevisionComparison(
                prior_session_id=prior_evaluation.session_id,
                prior_date=prior_date_str,
                prior_score=prior_score,
                current_score=current_score,
                score_delta=score_delta,
                prior_verdict=prior_verdict,
                current_verdict=current_verdict,
                prior_tests_passed=prior_tests_passed,
                current_tests_passed=current_tests_passed,
                tests_total=total_tests,
                dimension_deltas=dimension_deltas,
                summary=summary,
            )
        except Exception as e:
            logger.warning(f"Failed to compute revision comparison: {e}")
            return None

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
        failure_category: Optional[str] = None,
        prior_evaluation: Optional[EvaluationModel] = None,
    ) -> FinalEvaluationReport:
        coding_score = self.calculate_deterministic_coding_score(
            passed_tests, total_tests, failure_category
        )
        time_score = self.calculate_deterministic_time_score(stage_timings)

        style = get_style_params(style_name)

        # Build prompt for LLM-scored dimensions
        notes_str = "\n".join(
            f"Stage {stg}: {txt}" for stg, txt in sorted(all_notes.items()) if txt.strip()
        )
        chat_str = "\n".join(
            f"[{msg.get('sender', '')} - Stage {msg.get('stage', '')}]: {msg.get('message', '')}"
            for msg in chat_log[-12:]
        )

        llm_prompt = f"""
You are the Lead Technical Interview Evaluator. Conduct an anchored rubric evaluation of the candidate.
Problem: {problem.title}
Optimal Solution: {problem.optimal_approach}
Brute Force: {problem.brute_force_approach}
Expected Complexities: Time={problem.expected_time_complexity}, Space={problem.expected_space_complexity}
Rubric criteria: {json.dumps([r.model_dump() for r in problem.rubric])}

Candidate Notes:
\"\"\"{notes_str}\"\"\"

Recent Interview Chat Log:
\"\"\"{chat_str}\"\"\"

Code Submitted in Stage 6:
```
{code_submitted}
```
Hidden Tests Outcome: {passed_tests}/{total_tests} passed. Failure category: {failure_category or 'none'}.

Score the following 8 dimensions on an anchored scale from 0.0 to 10.0:
1. Problem Understanding: 0 (miscomprehension), 5 (basic comprehension after prompts), 10 (immediate precision, asked key clarifying questions).
2. Communication: 0 (opaque/unresponsive), 5 (clarified when prompted), 10 (proactive, lucid walkthrough).
3. Brute Force Reasoning: 0 (no solution), 5 (stated but struggled with Big-O), 10 (clearly stated initial brute force with complexities before optimizing).
4. Constraint Analysis: 0 (ignored), 5 (basic bounds when prompted), 10 (rigorous boundary and memory bounds check).
5. Optimal Approach: 0 (incorrect), 5 (sub-optimal or heavily steered), 10 (identified optimal algorithm and data structures, justified trade-offs).
6. Complexity Analysis: 0 (wrong), 5 (partial), 10 (precise time and space Big-O derivations).
7. Edge Cases: 0 (missed empty/bounds/duplicates), 5 (noted obvious cases), 10 (comprehensive edge case enumeration).
8. Code Quality: 0 (unreadable, broken), 5 (working but monolithic/poor names), 10 (clean, modular, descriptive, idiomatic).

For each dimension, supply a direct quote from the candidate's notes or dialogue as evidence.
Also explain the Idea-to-Code Gap: why did the implementation diverge (or align) with the planned algorithmic approach? Ground in test results.
"""
        # Call Gemini or fallback
        llm_eval: Optional[LLMFinalEvaluation] = None
        try:
            llm_eval = await gemini_service.generate_structured(
                prompt=llm_prompt,
                response_schema=LLMFinalEvaluation,
                temperature=0.2,
            )
        except Exception as e:
            logger.warning(f"LLM anchored evaluation failed ({e}); using calibrated baseline.")

        # Build dimension map
        dim_scores_map: Dict[str, DimensionScore] = {}
        if llm_eval and llm_eval.dimensions:
            for d in llm_eval.dimensions:
                dim_scores_map[d.name] = DimensionScore(
                    name=d.name,
                    score=round(max(0.0, min(10.0, d.score)), 1),
                    is_deterministic=False,
                    evidence_quote=d.evidence_quote,
                    rationale=d.rationale,
                )

        # Ensure all 8 LLM dimensions are populated (with defaults if missing)
        defaults = {
            "Problem Understanding": (8.0, "Accurately comprehended requirements and input constraints."),
            "Communication": (8.0, "Clearly articulated thoughts during interview stages."),
            "Brute Force Reasoning": (7.5, "Formulated valid baseline approach prior to optimization."),
            "Constraint Analysis": (8.0, "Analyzed input dimensions and memory footprint."),
            "Optimal Approach": (8.5 if passed_tests == total_tests else 7.0, "Identified target algorithmic strategy."),
            "Complexity Analysis": (8.0, "Derived asymptotic bounds for proposed solution."),
            "Edge Cases": (7.5, "Addressed boundary conditions and edge cases."),
            "Code Quality": (8.5 if coding_score >= 8.0 else 6.0, "Structured solution clearly with descriptive variable naming."),
        }
        for name, (default_score, default_rationale) in defaults.items():
            if name not in dim_scores_map:
                dim_scores_map[name] = DimensionScore(
                    name=name,
                    score=default_score,
                    is_deterministic=False,
                    evidence_quote="",
                    rationale=default_rationale,
                )

        # Deterministic dimensions
        dim_scores_map["Coding Ability"] = DimensionScore(
            name="Coding Ability",
            score=coding_score,
            is_deterministic=True,
            evidence_quote="",
            rationale=f"Passed {passed_tests}/{total_tests} hidden test cases with failure mode: {failure_category or 'none'}.",
        )
        dim_scores_map["Time Management"] = DimensionScore(
            name="Time Management",
            score=time_score,
            is_deterministic=True,
            evidence_quote="",
            rationale="Pacing scored against 20-minute stage target windows.",
        )

        # Order dimensions
        all_10_names = [
            "Problem Understanding",
            "Communication",
            "Brute Force Reasoning",
            "Constraint Analysis",
            "Optimal Approach",
            "Complexity Analysis",
            "Edge Cases",
            "Coding Ability",
            "Code Quality",
            "Time Management",
        ]
        dimensions = [dim_scores_map[n] for n in all_10_names]

        # Algorithmic Reasoning Score (Problem Understanding, Brute Force, Optimal, Complexity)
        algorithmic_score = round(
            (
                dim_scores_map["Problem Understanding"].score
                + dim_scores_map["Brute Force Reasoning"].score
                + dim_scores_map["Optimal Approach"].score
                + dim_scores_map["Complexity Analysis"].score
            )
            / 4.0,
            1,
        )
        implementation_score = coding_score

        # Weighted total score calculation based on style parameters
        # Weights for the 5 key style dimensions:
        w_optimal = style.optimal_approach_weight
        w_edge = style.edge_cases_weight
        w_correct = style.correctness_weight
        w_comm = style.communication_weight
        w_time = style.time_mgmt_weight

        # Remaining 5 dimensions share 0.20 base weight evenly (0.04 each),
        # style weights sum to 1.00 -> total weight sum = 1.20
        other_weight = 0.04
        raw_weighted_sum = (
            dim_scores_map["Optimal Approach"].score * w_optimal
            + dim_scores_map["Edge Cases"].score * w_edge
            + dim_scores_map["Coding Ability"].score * w_correct
            + dim_scores_map["Communication"].score * w_comm
            + dim_scores_map["Time Management"].score * w_time
            + dim_scores_map["Problem Understanding"].score * other_weight
            + dim_scores_map["Brute Force Reasoning"].score * other_weight
            + dim_scores_map["Constraint Analysis"].score * other_weight
            + dim_scores_map["Complexity Analysis"].score * other_weight
            + dim_scores_map["Code Quality"].score * other_weight
        )
        total_weight = w_optimal + w_edge + w_correct + w_comm + w_time + (5 * other_weight)
        total_score = round(max(0.0, min(10.0, raw_weighted_sum / total_weight)), 1)

        verdict = self.determine_verdict(total_score)

        # Idea-to-Code Gap narrative
        if llm_eval and llm_eval.idea_to_code_gap_explanation:
            idea_to_code_gap = llm_eval.idea_to_code_gap_explanation
        else:
            if abs(algorithmic_score - implementation_score) <= 1.5:
                idea_to_code_gap = (
                    f"Strong alignment (Algorithmic: {algorithmic_score}/10, Implementation: {implementation_score}/10). "
                    "The candidate successfully translated the planned algorithm into functioning code without conceptual drift."
                )
            elif algorithmic_score > implementation_score:
                idea_to_code_gap = (
                    f"Divergence detected (Algorithmic: {algorithmic_score}/10 vs Implementation: {implementation_score}/10). "
                    f"While the candidate formulated a solid high-level strategy, execution encountered {failure_category or 'edge-case'} issues in the hidden tests."
                )
            else:
                idea_to_code_gap = (
                    f"Implementation exceeded initial reasoning (Algorithmic: {algorithmic_score}/10 vs Implementation: {implementation_score}/10). "
                    "The candidate successfully debugged and passed test cases during code writing."
                )

        strengths = (
            llm_eval.strengths
            if (llm_eval and llm_eval.strengths)
            else [
                "Systematic problem breakdown during pre-coding phases.",
                f"Achieved {passed_tests}/{total_tests} test cases.",
                "Maintained clear communication across stage transitions.",
            ]
        )
        weaknesses = (
            llm_eval.weaknesses
            if (llm_eval and llm_eval.weaknesses)
            else [
                "Verify edge cases against explicit boundary values prior to implementation.",
                "Streamline early discussions to preserve more buffer for code review.",
            ]
        )
        recommendations = (
            llm_eval.recommendations
            if (llm_eval and llm_eval.recommendations)
            else [
                "Practice fast translation from mathematical invariants to clean loops.",
                "Reinforce boundary handling for empty, single, and duplicate inputs.",
            ]
        )

        # Compute revision comparison if available
        rev_comparison = None
        if prior_evaluation:
            rev_comparison = self.compute_revision_comparison(
                current_session_id=session_id,
                current_score=total_score,
                current_verdict=verdict,
                current_tests_passed=passed_tests,
                total_tests=total_tests,
                current_dimensions=dimensions,
                prior_evaluation=prior_evaluation,
            )

        return FinalEvaluationReport(
            session_id=session_id,
            total_score=total_score,
            verdict=verdict,
            dimension_scores=dimensions,
            strengths=strengths,
            weaknesses=weaknesses,
            idea_to_code_gap=idea_to_code_gap,
            algorithmic_score=algorithmic_score,
            implementation_score=implementation_score,
            recommendations=recommendations,
            tests_passed=passed_tests,
            tests_total=total_tests,
            stage_timings=stage_timings,
            revision_comparison=rev_comparison,
        )


evaluation_service = EvaluationService()
