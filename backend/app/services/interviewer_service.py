import logging
from typing import List, Optional, Union
from pydantic import BaseModel, Field
from ..schemas.problem import ProblemPublic, ProblemPublicBlind
from ..schemas.evaluation import EvaluatorSignal
from ..config.styles import get_style_params
from .gemini_service import gemini_service

logger = logging.getLogger("interviewer_service")


class InterviewerOutput(BaseModel):
    message: str = Field(description="Concise interviewer query, probe, or acknowledgement. Max 2-3 sentences. Never reveal hints or answers.")


class InterviewerService:
    async def get_response(
        self,
        problem: Union[ProblemPublic, ProblemPublicBlind],
        stage: int,
        style_name: str,
        candidate_message: str,
        candidate_notes: str,
        evaluator_signal: Optional[EvaluatorSignal] = None,
        is_blind: bool = False,
    ) -> str:
        """
        CRITICAL RULE:
        Zero LLM calls during coding stage (Stage 6).
        The caller must enforce this, but as defense-in-depth, we assert/raise if stage == 6.
        """
        if stage >= 6:
            raise ValueError("Zero LLM calls permitted in Coding stage (stage 6).")

        style = get_style_params(style_name)

        signal_info = ""
        if evaluator_signal:
            signal_info = f"Evaluator Signal: On Track={evaluator_signal.on_track}, Gap Type={evaluator_signal.gap_type}, Probe Type={evaluator_signal.probe_type}"

        blind_instructions = ""
        problem_header = ""
        if is_blind or isinstance(problem, ProblemPublicBlind):
            blind_instructions = (
                "- This is a BLIND mock interview. Server-side redaction is active.\n"
                "- NEVER mention the problem name, title, category, difficulty rating, or expected complexities.\n"
                "- Do NOT confirm or deny problem titles or categories if the candidate guesses them.\n"
            )
        else:
            problem_header = f"Problem: {getattr(problem, 'title', '')}\n"

        system_instruction = f"""
You are an expert technical interviewer conducting a live coding interview.
Tone: {style.tone}
Stage: Stage {stage} of 6.
Rules:
- You are an EVALUATOR, not a tutor or helper.
- NEVER give hints, suggestions, algorithms, data structures, or code.
- If the candidate asks for help or asks if they are right, ask them to justify their reasoning or consider edge cases.
- Keep your reply terse, professional, and limited to 1-3 sentences.
{blind_instructions}
"""

        prompt = f"""
{problem_header}Public Statement: {problem.statement}
Current Stage: {stage}
{signal_info}

Candidate's latest message:
\"{candidate_message}\"

Candidate's current notes for this stage:
\"{candidate_notes}\"

Reply to the candidate as the interviewer:
"""
        try:
            res = await gemini_service.generate_structured(
                prompt=prompt,
                response_schema=InterviewerOutput,
                temperature=0.2,
                system_instruction=system_instruction,
            )
            return res.message
        except Exception:
            # Fallback neutral responses by stage
            fallbacks = {
                1: "Understood. Have you considered whether the input contains negative numbers or duplicate elements?",
                2: "What would the brute-force time and space complexity be for that approach?",
                3: "Good. How do the input bounds affect your choice of algorithm?",
                4: "Could you walk through how you would optimize this beyond the brute force?",
                5: "What specific boundary or corner cases might break this approach?",
            }
            return fallbacks.get(stage, "Understood. Please continue with your reasoning.")


interviewer_service = InterviewerService()
