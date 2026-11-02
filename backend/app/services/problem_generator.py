import logging
from typing import Optional
from ..schemas.problem import ProblemPrivate
from ..schemas.session import InterviewConfig
from .gemini_service import gemini_service
from .problem_validator import problem_validator

logger = logging.getLogger("problem_generator")


class ProblemGenerator:
    async def generate_problem(self, config: InterviewConfig) -> ProblemPrivate:
        """
        Generates problem conforming to InterviewConfig and runs validation pipeline.
        Tries up to 3 times before raising an error.
        """
        prompt = f"""
Generate an algorithmic technical interview problem for:
- Source: {config.source}
- Category: {config.category}
- Difficulty: {config.difficulty}
- Target Language: {config.language}
- Framing: {config.framing}

Requirements:
1. Provide function signature, clear statement with 3 examples, constraints, visible tests.
2. Provide a 100% working Python reference solution and an independent Python brute-force solution.
3. Provide an input generator function `generate_inputs(n)` in Python returning a list of valid argument lists.
4. Provide hidden test cases covering edge cases.
5. Provide rubric items.
"""
        max_attempts = 3
        last_error = ""

        for attempt in range(1, max_attempts + 1):
            logger.info(f"Generating problem, attempt {attempt}/{max_attempts}")
            problem_candidate = await gemini_service.generate_structured(
                prompt=prompt,
                response_schema=ProblemPrivate,
                temperature=0.3,
            )

            # Ensure valid starter template exists
            if not problem_candidate.starter_code or config.language not in problem_candidate.starter_code:
                fn_name = problem_candidate.signature.function_name
                args_str = ", ".join(a.name for a in problem_candidate.signature.args)
                problem_candidate.starter_code = {
                    "python": f"def {fn_name}({args_str}):\n    # Your solution body here\n    pass\n"
                }

            # Run validation pipeline
            passed, msg = await problem_validator.validate_problem(problem_candidate)
            if passed:
                logger.info(f"Problem '{problem_candidate.title}' successfully validated on attempt {attempt}")
                return problem_candidate

            logger.warning(f"Problem validation failed on attempt {attempt}: {msg}")
            last_error = msg

        raise RuntimeError(f"Failed to generate valid problem after {max_attempts} attempts: {last_error}")


problem_generator = ProblemGenerator()
