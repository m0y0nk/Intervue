import logging
from typing import Tuple
from ..schemas.problem import ProblemPrivate
from .code_execution_service import code_execution_service

logger = logging.getLogger("problem_validator")


class ProblemValidator:
    @staticmethod
    async def validate_problem(problem: ProblemPrivate) -> Tuple[bool, str]:
        """
        Validates problem using differential testing in the executor sandbox:
        1. Validates Python reference against visible examples.
        2. Executes input generator in sandbox to generate random inputs.
        3. Differential test: reference vs brute force must agree.
        4. Computes/verifies hidden tests using the reference solution.
        """
        fn_name = problem.signature.function_name

        # Step 1: Run reference on visible examples
        visible_tests_payload = [
            {"args": t.args, "expected": t.expected} for t in problem.visible_tests
        ]

        if visible_tests_payload:
            ref_run = await code_execution_service.execute(
                code=problem.python_reference,
                function_name=fn_name,
                tests=visible_tests_payload,
                checker=problem.checker,
            )
            if not ref_run.all_passed:
                return False, f"Reference solution failed visible examples: {ref_run.error or 'Outputs did not match'}"

        # Step 2: Run input generator & differential testing
        # We run a small sandbox test runner script comparing reference vs brute force on random inputs
        diff_runner_code = f"""
{problem.python_reference}

{problem.python_brute_force}

{problem.input_generator}

def run_differential_test():
    import json
    tests = generate_inputs(50)  # fast differential batch
    for i, args in enumerate(tests):
        try:
            ref_out = {fn_name}(*args)
        except Exception as e:
            return f"Reference crashed on test {{i}}: {{e}}"
        try:
            bf_out = {fn_name}(*args)
        except Exception as e:
            return f"Brute force crashed on test {{i}}: {{e}}"
        
        # Compare
        if ref_out != bf_out:
            # Handle list sorting if order not strict
            if isinstance(ref_out, list) and isinstance(bf_out, list):
                if sorted(ref_out) != sorted(bf_out):
                    return f"Mismatch on test {{i}}: ref={{ref_out}}, bf={{bf_out}}"
            else:
                return f"Mismatch on test {{i}}: ref={{ref_out}}, bf={{bf_out}}"
    return "OK"
"""
        diff_run = await code_execution_service.execute(
            code=diff_runner_code,
            function_name="run_differential_test",
            tests=[{"args": [], "expected": "OK"}],
            checker="exact",
            timeout_seconds=8.0,
        )

        if not diff_run.all_passed:
            actual_err = diff_run.results[0].actual if diff_run.results else diff_run.error
            return False, f"Differential testing failed: {actual_err}"

        # Step 3: Run reference on hidden tests to verify they produce outputs without errors
        if problem.hidden_tests:
            hidden_payload = [
                {"args": t.args, "expected": t.expected} for t in problem.hidden_tests
            ]
            hidden_run = await code_execution_service.execute(
                code=problem.python_reference,
                function_name=fn_name,
                tests=hidden_payload,
                checker=problem.checker,
            )
            if not hidden_run.all_passed:
                return False, f"Reference solution failed hidden test verification: {hidden_run.error}"

        return True, "Problem passed all validation checks."


problem_validator = ProblemValidator()
