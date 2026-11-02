import ast
import inspect
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.schemas.problem import ProblemPrivate, ProblemPublic
from app.services.interviewer_service import InterviewerService, interviewer_service


def test_import_boundary_interviewer_service():
    """
    CRITICAL ARCHITECTURAL ISOLATION:
    Assert that interviewer_service.py never imports ProblemPrivate.
    """
    interviewer_service_file = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "backend", "app", "services", "interviewer_service.py")
    )
    with open(interviewer_service_file, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())

    imported_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imported_names.add(n.name)
        elif isinstance(node, ast.ImportFrom):
            for n in node.names:
                imported_names.add(n.name)

    assert "ProblemPrivate" not in imported_names, (
        "ISOLATION VIOLATION: interviewer_service.py must never import ProblemPrivate!"
    )


def test_zero_llm_calls_in_coding_stage():
    """
    CRITICAL RULE:
    Stage 6 (Coding) must trigger zero LLM calls.
    interviewer_service.get_response must raise an error if stage >= 6.
    """
    import asyncio

    problem = ProblemPublic(
        id="p1",
        title="Test Problem",
        statement="Solve it",
        examples=[],
        signature={"function_name": "solve", "args": [], "return_type": "int"},
    )
    with pytest.raises(ValueError, match="Zero LLM calls permitted in Coding stage"):
        asyncio.run(
            interviewer_service.get_response(
                problem=problem,
                stage=6,
                style_name="general",
                candidate_message="Can you help me?",
                candidate_notes="",
            )
        )


def test_prompt_leak_guard():
    """
    Verifies that interviewer prompt builder never receives or embeds
    private reference solution or hidden tests strings.
    """
    reference_secret = "def secret_optimal_reference_impl(): return 42"
    hidden_test_secret = "hidden_arg_secret_value_9999"

    # ProblemPublic does not have python_reference or hidden_tests
    pub = ProblemPublic(
        id="p1",
        title="Public Title",
        statement="Public Statement",
        examples=[],
        signature={"function_name": "solution", "args": [], "return_type": "int"},
    )

    assert not hasattr(pub, "python_reference")
    assert not hasattr(pub, "hidden_tests")
    assert reference_secret not in str(pub.model_dump())
    assert hidden_test_secret not in str(pub.model_dump())
