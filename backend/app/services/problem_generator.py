"""
Problem Generator — routes to the appropriate generation strategy based on source.

Sources:
  random_dsa  — Gemini picks a DSA problem matching difficulty/category/framing.
  ai_business — Gemini invents a business scenario that hides the underlying algorithm.
  leetcode    — User pastes a statement; Gemini converts it to ProblemPrivate schema;
                validation pipeline runs. Title/category/difficulty never revealed.
  custom      — User pastes any statement; same pipeline. Marked unsupported if
                validation fails after retries.
  adaptive    — Adaptive practice service computes target category/difficulty from
                history; generation then follows random_dsa path.

All sources feed the same ProblemPrivate structure and validation pipeline.
"""

import hashlib
import logging
from typing import Optional

from sqlalchemy.orm import Session as DBSession

from ..schemas.problem import ProblemPrivate, generate_starter_templates
from ..schemas.session import InterviewConfig
from .gemini_service import gemini_service
from .problem_validator import problem_validator

logger = logging.getLogger("problem_generator")

MAX_ATTEMPTS = 3

# Business domains to cycle through for ai_business source
BUSINESS_DOMAINS = [
    "e-commerce order fulfillment",
    "logistics route planning",
    "financial transaction processing",
    "social network feed ranking",
    "cloud infrastructure scheduling",
    "video streaming buffering",
    "healthcare appointment scheduling",
    "supply chain inventory management",
]


class ProblemGenerationError(Exception):
    """Raised when a problem could not be generated/validated after retries."""
    pass


class UnsupportedProblemError(ProblemGenerationError):
    """Raised when a custom/leetcode problem fails validation and cannot be used."""
    pass


class ProblemGenerator:

    async def generate_problem(
        self,
        config: InterviewConfig,
        db: Optional[DBSession] = None,
        # Source-specific extras
        leetcode_id: Optional[str] = None,
        leetcode_statement: Optional[str] = None,
        custom_statement: Optional[str] = None,
        custom_url: Optional[str] = None,
        custom_extra_constraints: Optional[str] = None,
    ) -> ProblemPrivate:
        """
        Dispatch to the correct generator and run the validation pipeline.
        """
        source = config.source

        if source == "random_dsa":
            return await self._generate_random_dsa(config)
        elif source == "ai_business":
            return await self._generate_ai_business(config)
        elif source == "adaptive":
            return await self._generate_adaptive(config, db)
        elif source == "leetcode":
            return await self._generate_leetcode(
                config, leetcode_id=leetcode_id, statement=leetcode_statement
            )
        elif source == "custom":
            return await self._generate_custom(
                config,
                statement=custom_statement,
                url=custom_url,
                extra_constraints=custom_extra_constraints,
            )
        else:
            raise ProblemGenerationError(f"Unknown source: {source}")

    # ------------------------------------------------------------------ #
    #  random_dsa                                                         #
    # ------------------------------------------------------------------ #
    async def _generate_random_dsa(self, config: InterviewConfig) -> ProblemPrivate:
        prompt = self._random_dsa_prompt(config)
        return await self._generate_and_validate(prompt, config, "random_dsa")

    def _random_dsa_prompt(self, config: InterviewConfig, extra: str = "") -> str:
        framing_note = (
            "Wrap the problem as a realistic business scenario "
            "(e.g. e-commerce, logistics, finance). "
            "NEVER name the algorithm or data structure in the problem statement."
            if config.framing == "business"
            else ""
        )
        avoid_note = extra  # e.g. avoid problem IDs
        return f"""
Generate a technical interview problem with the following parameters:
- Category: {config.category}
- Difficulty: {config.difficulty}
- Language: {config.language}
{framing_note}
{avoid_note}

Requirements:
1. Function signature, clear statement with at least 3 examples, constraints.
2. 100% working Python reference solution.
3. Independent Python brute-force solution (simpler, possibly slower).
4. Python input generator `generate_inputs(n=10)` returning a list of small argument lists (lengths <= 15) for fast differential testing.
5. Hidden test cases (at least 4) covering edge cases.
6. Rubric items aligned to the 6 interview stages.
7. NEVER name the algorithm, data structure, or give away the solution approach.
"""

    # ------------------------------------------------------------------ #
    #  ai_business                                                        #
    # ------------------------------------------------------------------ #
    async def _generate_ai_business(self, config: InterviewConfig) -> ProblemPrivate:
        import random
        domain = random.choice(BUSINESS_DOMAINS)
        prompt = f"""
You are designing a real technical interview question for a {domain} company.

Create a **business-framed** DSA interview problem where:
- The surface story is about a real business need (orders, routes, feeds, transactions, etc.)
- The underlying algorithm is a well-known DSA problem (do NOT name the algorithm).
- At least 3 concrete examples with business-meaningful variable names.
- Category hint: {config.category} — choose a problem fitting this topic but frame it as a business problem.
- Difficulty: {config.difficulty}
- The statement must be solvable in 20 minutes, unambiguous, have a unique optimal solution.
- NEVER use algorithm names (e.g. "sliding window", "dynamic programming", "graph") in the statement.
- NEVER name the data structure in the statement (e.g. "use a hash map").

Requirements:
1. Function signature, clear business-story statement with at least 3 examples, constraints.
2. 100% working Python reference solution.
3. Independent Python brute-force solution.
4. Python input generator `generate_inputs(n=10)` returning a list of small argument lists (lengths <= 15) for fast differential testing.
5. Hidden test cases (at least 4).
6. Rubric items aligned to the 6 interview stages.
"""
        return await self._generate_and_validate(prompt, config, "ai_business")

    # ------------------------------------------------------------------ #
    #  adaptive                                                           #
    # ------------------------------------------------------------------ #
    async def _generate_adaptive(
        self, config: InterviewConfig, db: Optional[DBSession]
    ) -> ProblemPrivate:
        if db is None:
            raise ProblemGenerationError(
                "Adaptive source requires a database session for history analysis."
            )

        from .adaptive_practice_service import compute_adaptive_profile

        profile = compute_adaptive_profile(db)
        logger.info(f"Adaptive profile: {profile.rationale}")

        # Build an augmented config with the computed category/difficulty
        adaptive_config = InterviewConfig(
            source="adaptive",
            mode=config.mode,
            style=config.style,
            difficulty=profile.target_difficulty,
            category=profile.target_category,
            language=config.language,
            framing=config.framing,
            duration=config.duration,
        )

        # Dedup: tell Gemini to avoid previously attempted problems
        avoid_ids = profile.attempted_problem_ids[:10]
        avoid_note = (
            f"Avoid problems similar to these previously attempted problem IDs: {avoid_ids}. "
            "Pick a fresh problem the candidate has not seen before."
            if avoid_ids
            else ""
        )

        prompt = self._random_dsa_prompt(adaptive_config, extra=avoid_note)
        problem = await self._generate_and_validate(prompt, adaptive_config, "adaptive")

        # Attach adaptive rationale as a hint to the private model
        problem.optimal_approach = (
            f"[Adaptive selection rationale: {profile.rationale}]\n\n"
            + problem.optimal_approach
        )
        return problem

    # ------------------------------------------------------------------ #
    #  leetcode                                                           #
    # ------------------------------------------------------------------ #
    async def _generate_leetcode(
        self,
        config: InterviewConfig,
        leetcode_id: Optional[str],
        statement: Optional[str],
    ) -> ProblemPrivate:
        if not statement or len(statement.strip()) < 50:
            raise ProblemGenerationError(
                "LeetCode source requires a pasted problem statement "
                "(at least 50 characters). "
                "LeetCode has no official public API; please paste the full statement."
            )

        id_note = f"The user says this is LeetCode problem #{leetcode_id}. " if leetcode_id else ""

        prompt = f"""
{id_note}The user has pasted the following problem statement verbatim from LeetCode:

---
{statement.strip()}
---

Your task:
1. Parse and preserve the statement, examples, and constraints EXACTLY as given.
2. Convert to the standard ProblemPrivate schema.
3. Generate a 100% correct Python reference solution.
4. Generate an independent Python brute-force solution.
5. Generate `generate_inputs(n)` respecting the stated constraints.
6. Generate hidden test cases (at least 4 edge cases).
7. Generate rubric items.

CRITICAL RULES:
- Do NOT reveal the problem title or LeetCode ID in the public statement field.
  Set `title` to a generic description (e.g. "Array Subsequence Challenge").
- Do NOT reveal difficulty or category in the statement.
- Do NOT include any editorial hints or known optimal approaches in the statement.
- Preserve all examples and constraints from the pasted text faithfully.
"""
        problem = await self._generate_and_validate(prompt, config, "leetcode")

        # Fingerprint from statement hash to avoid duplicates
        stmt_hash = hashlib.sha256(statement.encode()).hexdigest()[:16]
        problem.fingerprint = f"lc_{leetcode_id or 'paste'}_{stmt_hash}"
        return problem

    # ------------------------------------------------------------------ #
    #  custom                                                             #
    # ------------------------------------------------------------------ #
    async def _generate_custom(
        self,
        config: InterviewConfig,
        statement: Optional[str],
        url: Optional[str],
        extra_constraints: Optional[str],
    ) -> ProblemPrivate:
        if not statement or len(statement.strip()) < 30:
            raise ProblemGenerationError(
                "Custom source requires a problem statement (at least 30 characters)."
            )

        url_note = f"Source URL: {url}\n" if url else ""
        constraints_note = (
            f"Additional constraints from the user:\n{extra_constraints}\n"
            if extra_constraints
            else ""
        )

        prompt = f"""
The user has provided a custom problem statement for a technical interview:

---
{url_note}{statement.strip()}
{constraints_note}
---

Your task:
1. Parse the statement and convert to the ProblemPrivate schema.
2. Generate a 100% correct Python reference solution.
   - If the problem is ambiguous or requires external data (e.g. a database, network call),
     you MUST respond with an empty `python_reference` and set `title` to "UNSUPPORTED".
3. Generate an independent Python brute-force solution.
4. Generate `generate_inputs(n)` respecting the constraints.
5. Generate hidden test cases (at least 4 edge cases).
6. Generate rubric items.

If the problem is not solvable as a pure function (e.g. requires I/O, external state,
design questions without clear input/output), set `title = "UNSUPPORTED"` and
`python_reference = ""`.
"""
        try:
            problem = await self._generate_and_validate(prompt, config, "custom")
        except ProblemGenerationError as e:
            raise UnsupportedProblemError(
                f"Custom problem could not be validated and is marked unsupported: {e}"
            )

        if problem.title.strip().upper() == "UNSUPPORTED":
            raise UnsupportedProblemError(
                "The custom problem cannot be reliably converted to a testable function. "
                "It may require I/O, external state, or is otherwise not suitable for "
                "automated verification. Please provide a problem with clear function "
                "input/output requirements."
            )

        return problem

    # ------------------------------------------------------------------ #
    #  Shared: generate + validate loop                                   #
    # ------------------------------------------------------------------ #
    async def _generate_and_validate(
        self, prompt: str, config: InterviewConfig, source_label: str
    ) -> ProblemPrivate:
        last_error = ""

        for attempt in range(1, MAX_ATTEMPTS + 1):
            logger.info(
                f"[{source_label}] Generating problem, attempt {attempt}/{MAX_ATTEMPTS}"
            )
            try:
                candidate = await gemini_service.generate_structured(
                    prompt=prompt,
                    response_schema=ProblemPrivate,
                    temperature=0.3,
                )
            except Exception as e:
                last_error = str(e)
                logger.warning(f"[{source_label}] Gemini call failed: {e}")
                continue

            # Merge/complete starter templates
            starter_templates = generate_starter_templates(candidate.signature)
            if candidate.starter_code:
                starter_templates.update(candidate.starter_code)
            candidate.starter_code = starter_templates

            # Ensure category/difficulty populated from config if missing
            if not candidate.category or candidate.category == "mixed":
                candidate.category = config.category
            if not candidate.difficulty:
                candidate.difficulty = config.difficulty

            passed, msg = await problem_validator.validate_problem(candidate)
            if passed:
                logger.info(
                    f"[{source_label}] Problem '{candidate.title}' validated "
                    f"on attempt {attempt}"
                )
                return candidate

            logger.warning(
                f"[{source_label}] Validation failed on attempt {attempt}: {msg}"
            )
            last_error = msg

        raise ProblemGenerationError(
            f"Failed to generate a valid {source_label} problem after "
            f"{MAX_ATTEMPTS} attempts: {last_error}"
        )


problem_generator = ProblemGenerator()
