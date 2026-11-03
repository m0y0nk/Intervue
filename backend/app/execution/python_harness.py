#!/usr/bin/env python3
"""
Python execution harness for AI Technical Interview Simulator.
Parses JSON payload from stdin, executes candidate solution against test cases,
validates outputs against expected data, and outputs structured JSON to stdout.
"""

import sys
import json
import time
import math
import traceback
from typing import Any, List, Optional, Tuple


class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

    def to_list(self) -> List[Any]:
        res = []
        curr = self
        visited = set()
        while curr:
            if id(curr) in visited:
                break  # cycle protection
            visited.add(id(curr))
            res.append(curr.val)
            curr = curr.next
        return res

    @staticmethod
    def from_list(vals: List[Any]) -> Optional["ListNode"]:
        if not vals:
            return None
        head = ListNode(vals[0])
        curr = head
        for v in vals[1:]:
            curr.next = ListNode(v)
            curr = curr.next
        return head


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

    def to_level_order(self) -> List[Any]:
        if not self:
            return []
        res = []
        queue = [self]
        while queue:
            node = queue.pop(0)
            if node:
                res.append(node.val)
                queue.append(node.left)
                queue.append(node.right)
            else:
                res.append(None)
        while res and res[-1] is None:
            res.pop()
        return res

    @staticmethod
    def from_level_order(vals: List[Any]) -> Optional["TreeNode"]:
        if not vals or vals[0] is None:
            return None
        root = TreeNode(vals[0])
        queue = [root]
        idx = 1
        while queue and idx < len(vals):
            curr = queue.pop(0)
            if idx < len(vals) and vals[idx] is not None:
                curr.left = TreeNode(vals[idx])
                queue.append(curr.left)
            idx += 1
            if idx < len(vals) and vals[idx] is not None:
                curr.right = TreeNode(vals[idx])
                queue.append(curr.right)
            idx += 1
        return root


def serialize_val(val: Any) -> Any:
    if isinstance(val, ListNode):
        return val.to_list()
    elif isinstance(val, TreeNode):
        return val.to_level_order()
    elif isinstance(val, tuple):
        return list(val)
    elif isinstance(val, set):
        return sorted(list(val))
    return val


def deserialize_arg(arg: Any, type_hint: Optional[str] = None) -> Any:
    if type_hint == "ListNode" and isinstance(arg, list):
        return ListNode.from_list(arg)
    if type_hint == "TreeNode" and isinstance(arg, list):
        return TreeNode.from_level_order(arg)
    return arg


def check_equal(actual: Any, expected: Any, checker: str = "exact") -> bool:
    actual = serialize_val(actual)
    expected = serialize_val(expected)

    if checker == "unordered":
        if isinstance(actual, list) and isinstance(expected, list):
            try:
                return sorted(actual) == sorted(expected)
            except TypeError:
                return [sorted(x) if isinstance(x, list) else x for x in actual] == [
                    sorted(x) if isinstance(x, list) else x for x in expected
                ]
    elif checker.startswith("float_tolerance"):
        eps = 1e-5
        if "(" in checker:
            try:
                eps = float(checker.split("(")[1].rstrip(")"))
            except Exception:
                eps = 1e-5
        if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
            return math.isclose(actual, expected, abs_tol=eps)
    elif checker == "valid_palindrome":
        s = str(actual)
        clean = "".join(c.lower() for c in s if c.isalnum())
        return clean == clean[::-1]

    if (actual is None and expected == []) or (actual == [] and expected is None):
        return True
    return actual == expected


def main():
    try:
        raw_input = ""
        import os
        payload_file = "/sandbox/test_data/payload.json"
        if os.path.exists(payload_file):
            with open(payload_file, "r", encoding="utf-8") as f:
                raw_input = f.read()
        else:
            raw_input = sys.stdin.read()

        if not raw_input:
            print(json.dumps({"status": "runtime_error", "error": "No input payload received"}))
            return
        payload = json.loads(raw_input)
    except Exception as e:
        print(json.dumps({"status": "runtime_error", "error": f"Failed to parse payload: {e}"}))
        return

    code = payload.get("code", "")
    function_name = payload.get("function_name", "solution")
    tests = payload.get("tests", [])
    checker = payload.get("checker", "exact")
    type_hints = payload.get("type_hints", [])

    # Namespace setup
    exec_globals = {
        "ListNode": ListNode,
        "TreeNode": TreeNode,
        "List": List,
        "Optional": Optional,
        "Tuple": Tuple,
        "Any": Any,
    }

    try:
        compiled = compile(code, "<candidate_code>", "exec")
        exec(compiled, exec_globals)
    except Exception as e:
        print(
            json.dumps(
                {
                    "status": "compilation_error",
                    "compile_error": traceback.format_exc(limit=3),
                    "results": [],
                }
            )
        )
        return

    fn = exec_globals.get(function_name)
    if not fn or not callable(fn):
        # Fallback: check if defined inside class Solution
        sol_cls = exec_globals.get("Solution")
        if sol_cls and isinstance(sol_cls, type):
            try:
                sol_inst = sol_cls()
                if hasattr(sol_inst, function_name) and callable(getattr(sol_inst, function_name)):
                    fn = getattr(sol_inst, function_name)
            except Exception:
                pass

    if not fn or not callable(fn):
        # Fallback: search for first user-defined function or method
        for k, v in exec_globals.items():
            if callable(v) and getattr(v, "__module__", None) in (None, "__main__") and k not in ("ListNode", "TreeNode", "Solution"):
                fn = v
                break

    if not fn or not callable(fn):
        print(
            json.dumps(
                {
                    "status": "runtime_error",
                    "error": f"Function '{function_name}' not found or not callable",
                    "results": [],
                }
            )
        )
        return

    results = []
    all_passed = True

    for t in tests:
        raw_args = t.get("args", [])
        expected = t.get("expected")

        deserialized_args = []
        for i, a in enumerate(raw_args):
            hint = type_hints[i] if i < len(type_hints) else None
            deserialized_args.append(deserialize_arg(a, hint))

        t0 = time.perf_counter()
        passed = False
        actual = None
        error_msg = None

        try:
            actual = fn(*deserialized_args)
            if actual is None and len(deserialized_args) > 0 and expected is not None and expected != []:
                actual = deserialized_args[0]
            passed = check_equal(actual, expected, checker)
        except Exception as e:
            error_msg = traceback.format_exc(limit=3)
            passed = False

        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        if not passed:
            all_passed = False

        results.append(
            {
                "passed": passed,
                "input": raw_args,
                "expected": expected,
                "actual": serialize_val(actual) if error_msg is None else None,
                "error": error_msg,
                "duration_ms": duration_ms,
            }
        )

    print(
        json.dumps(
            {
                "status": "success" if all_passed else "failed",
                "all_passed": all_passed,
                "results": results,
            }
        )
    )


if __name__ == "__main__":
    main()
