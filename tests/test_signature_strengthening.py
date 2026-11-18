import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.schemas.problem import (
    FunctionArg,
    FunctionSignature,
    generate_starter_templates,
    normalize_type,
    reconcile_signature_with_tests,
)


def test_normalize_type_variations():
    assert normalize_type("int") == "int"
    assert normalize_type("Integer") == "int"
    assert normalize_type("long") == "long"
    assert normalize_type("double") == "double"
    assert normalize_type("float") == "double"
    assert normalize_type("bool") == "bool"
    assert normalize_type("boolean") == "bool"
    assert normalize_type("str") == "string"
    assert normalize_type("String") == "string"
    assert normalize_type("void") == "void"
    assert normalize_type("None") == "void"

    # 1D arrays
    assert normalize_type("int[]") == "int[]"
    assert normalize_type("int []") == "int[]"
    assert normalize_type("Integer[]") == "int[]"
    assert normalize_type("List[int]") == "int[]"
    assert normalize_type("list[int]") == "int[]"
    assert normalize_type("List<Integer>") == "int[]"
    assert normalize_type("vector<int>") == "int[]"
    assert normalize_type("std::vector<int>&") == "int[]"

    # Strings
    assert normalize_type("string[]") == "string[]"
    assert normalize_type("String[]") == "string[]"
    assert normalize_type("List[str]") == "string[]"
    assert normalize_type("vector<string>") == "string[]"

    # 2D arrays
    assert normalize_type("int[][]") == "int[][]"
    assert normalize_type("List[List[int]]") == "int[][]"
    assert normalize_type("vector<vector<int>>") == "int[][]"

    # Data structures
    assert normalize_type("ListNode") == "ListNode"
    assert normalize_type("Optional[ListNode]") == "ListNode"
    assert normalize_type("ListNode*") == "ListNode"
    assert normalize_type("TreeNode") == "TreeNode"


def test_two_sum_signature_and_template_generation():
    """
    Test that even if a model generates Python-style List[int] or generic names,
    the Java template generates public int[] twoSum(int[] nums, int target),
    NOT public void twoSum(Object nums, int target)!
    """
    sig = FunctionSignature(
        function_name="twoSum",
        args=[
            FunctionArg(name="nums", type="List[int]"),
            FunctionArg(name="target", type="int"),
        ],
        return_type="List[int]",
    )
    tests = [
        {"args": [[2, 7, 11, 15], 9], "expected": [0, 1]},
        {"args": [[3, 2, 4], 6], "expected": [1, 2]},
    ]

    templates = generate_starter_templates(sig, tests)
    java_code = templates["java"]
    python_code = templates["python"]
    cpp_code = templates["cpp"]

    # Java assertions
    assert "public int[] twoSum(int[] nums, int target)" in java_code
    assert "return new int[]{};" in java_code
    assert "Object nums" not in java_code
    assert "public void twoSum" not in java_code
    assert "In-place modification" not in java_code

    # Python assertions
    assert "def twoSum(nums: list[int], target: int) -> list[int]:" in python_code

    # C++ assertions
    assert "std::vector<int> twoSum(std::vector<int>& nums, int target)" in cpp_code


def test_reconcile_signature_with_missing_or_object_types():
    """
    Test that if Gemini produces Object or void by mistake for Two Sum,
    reconcile_signature_with_tests restores int[] and int from the test inputs and outputs.
    """
    hallucinated_sig = FunctionSignature(
        function_name="two_sum",
        args=[
            FunctionArg(name="nums", type="Object"),
            FunctionArg(name="target", type="int"),
        ],
        return_type="void",
    )
    tests = [
        {"args": [[2, 7, 11, 15], 9], "expected": [0, 1]},
    ]

    reconciled = reconcile_signature_with_tests(hallucinated_sig, tests)
    assert reconciled.args[0].type == "int[]"
    assert reconciled.args[1].type == "int"
    assert reconciled.return_type == "int[]"

    templates = generate_starter_templates(reconciled)
    assert "public int[] twoSum(int[] nums, int target)" in templates["java"]
    assert "return new int[]{};" in templates["java"]


def test_in_place_void_problem():
    """
    Test in-place problems (e.g. Sort Colors) correctly keep void return type.
    """
    sig = FunctionSignature(
        function_name="sortColors",
        args=[FunctionArg(name="nums", type="int[]")],
        return_type="void",
    )
    tests = [
        {"args": [[2, 0, 2, 1, 1, 0]], "expected": None},
    ]
    templates = generate_starter_templates(sig, tests)
    assert "public void sortColors(int[] nums)" in templates["java"]
    assert "// In-place modification, no return needed" in templates["java"]
