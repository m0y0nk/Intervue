#!/usr/bin/env python3
"""
Java execution harness for AI Technical Interview Simulator.
Compiles candidate code and dynamic harness in sandbox /tmp, executes tests,
validates results against expected JSON outputs, and returns structured JSON to stdout.
"""

import sys
import json
import time
import math
import os
import subprocess
import traceback
from typing import Any, List, Optional


def escape_java_string(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r") + '"'


def to_java_literal(val: Any, type_hint: Optional[str] = None) -> str:
    if val is None:
        return "null"

    # Type hint based conversions
    if type_hint == "ListNode" or (isinstance(val, list) and type_hint == "ListNode"):
        inner = ", ".join(str(x) for x in val)
        return f"buildList(new int[]{{{inner}}})"

    if type_hint == "TreeNode" or (isinstance(val, list) and type_hint == "TreeNode"):
        inner = ", ".join("null" if x is None else str(x) for x in val)
        return f"buildTree(new Integer[]{{{inner}}})"

    if isinstance(val, bool):
        return "true" if val else "false"

    if isinstance(val, (int, float)):
        if type_hint == "double":
            return f"{float(val)}"
        if type_hint == "long" and isinstance(val, int):
            return f"{val}L"
        return str(val)

    if isinstance(val, str):
        return escape_java_string(val)

    if isinstance(val, list):
        if not val:
            if type_hint == "int[][]":
                return "new int[][]{}"
            if type_hint == "string[]":
                return "new String[]{}"
            return "new int[]{}"

        # 2D array
        if isinstance(val[0], list):
            rows = ", ".join("{" + ", ".join(str(x) for x in row) + "}" for row in val)
            return f"new int[][]{{{rows}}}"

        # String array
        if isinstance(val[0], str) or type_hint == "string[]":
            items = ", ".join(escape_java_string(str(x)) for x in val)
            return f"new String[]{{{items}}}"

        # 1D int array
        items = ", ".join(str(x) for x in val)
        return f"new int[]{{{items}}}"

    return str(val)


def check_equal(actual: Any, expected: Any, checker: str = "exact") -> bool:
    if checker == "unordered":
        if isinstance(actual, list) and isinstance(expected, list):
            try:
                return sorted(actual) == sorted(expected)
            except Exception:
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


HARNESS_TEMPLATE = """
import java.util.*;
import java.io.*;

class ListNode {
    public int val;
    public ListNode next;
    public ListNode() {}
    public ListNode(int val) { this.val = val; }
    public ListNode(int val, ListNode next) { this.val = val; this.next = next; }
}

class TreeNode {
    public int val;
    public TreeNode left;
    public TreeNode right;
    public TreeNode() {}
    public TreeNode(int val) { this.val = val; }
    public TreeNode(int val, TreeNode left, TreeNode right) {
        this.val = val;
        this.left = left;
        this.right = right;
    }
}

public class Harness {
    public static ListNode buildList(int[] vals) {
        if (vals == null || vals.length == 0) return null;
        ListNode dummy = new ListNode(0);
        ListNode curr = dummy;
        for (int v : vals) {
            curr.next = new ListNode(v);
            curr = curr.next;
        }
        return dummy.next;
    }

    public static TreeNode buildTree(Integer[] vals) {
        if (vals == null || vals.length == 0 || vals[0] == null) return null;
        TreeNode root = new TreeNode(vals[0]);
        Queue<TreeNode> queue = new LinkedList<>();
        queue.add(root);
        int i = 1;
        while (!queue.isEmpty() && i < vals.length) {
            TreeNode curr = queue.poll();
            if (i < vals.length && vals[i] != null) {
                curr.left = new TreeNode(vals[i]);
                queue.add(curr.left);
            }
            i++;
            if (i < vals.length && vals[i] != null) {
                curr.right = new TreeNode(vals[i]);
                queue.add(curr.right);
            }
            i++;
        }
        return root;
    }

    public static String serialize(Object obj) {
        if (obj == null) return "null";
        if (obj instanceof Boolean) return obj.toString();
        if (obj instanceof Number) return obj.toString();
        if (obj instanceof String) return "\\"" + ((String) obj).replace("\\\\", "\\\\\\\\").replace("\\"", "\\\\\\"") + "\\"";

        if (obj instanceof int[]) {
            StringBuilder sb = new StringBuilder("[");
            int[] arr = (int[]) obj;
            for (int i = 0; i < arr.length; i++) {
                if (i > 0) sb.append(", ");
                sb.append(arr[i]);
            }
            return sb.append("]").toString();
        }

        if (obj instanceof int[][]) {
            StringBuilder sb = new StringBuilder("[");
            int[][] mat = (int[][]) obj;
            for (int i = 0; i < mat.length; i++) {
                if (i > 0) sb.append(", ");
                sb.append(serialize(mat[i]));
            }
            return sb.append("]").toString();
        }

        if (obj instanceof String[]) {
            StringBuilder sb = new StringBuilder("[");
            String[] arr = (String[]) obj;
            for (int i = 0; i < arr.length; i++) {
                if (i > 0) sb.append(", ");
                sb.append(serialize(arr[i]));
            }
            return sb.append("]").toString();
        }

        if (obj instanceof List) {
            StringBuilder sb = new StringBuilder("[");
            List<?> list = (List<?>) obj;
            for (int i = 0; i < list.size(); i++) {
                if (i > 0) sb.append(", ");
                sb.append(serialize(list.get(i)));
            }
            return sb.append("]").toString();
        }

        if (obj instanceof ListNode) {
            StringBuilder sb = new StringBuilder("[");
            ListNode curr = (ListNode) obj;
            Set<ListNode> seen = new HashSet<>();
            int count = 0;
            while (curr != null && count < 10000) {
                if (seen.contains(curr)) break;
                seen.add(curr);
                if (count > 0) sb.append(", ");
                sb.append(curr.val);
                curr = curr.next;
                count++;
            }
            return sb.append("]").toString();
        }

        if (obj instanceof TreeNode) {
            List<String> list = new ArrayList<>();
            Queue<TreeNode> queue = new LinkedList<>();
            queue.add((TreeNode) obj);
            while (!queue.isEmpty()) {
                TreeNode node = queue.poll();
                if (node != null) {
                    list.add(String.valueOf(node.val));
                    queue.add(node.left);
                    queue.add(node.right);
                } else {
                    list.add("null");
                }
            }
            while (!list.isEmpty() && list.get(list.size() - 1).equals("null")) {
                list.remove(list.size() - 1);
            }
            return "[" + String.join(", ", list) + "]";
        }

        return "\\"" + obj.toString() + "\\"";
    }

    public static void main(String[] args) {
        Solution sol = new Solution();
        TEST_INVOCATIONS
    }
}
"""


def main():
    try:
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

    work_dir = "/tmp"

    # Write Solution.java
    # If the user did not wrap code in class Solution, wrap it
    if "class Solution" not in code:
        code_to_write = f"import java.util.*;\n\npublic class Solution {{\n{code}\n}}\n"
    else:
        # ensure public class Solution
        code_to_write = f"import java.util.*;\n\n{code}\n"
        if "public class Solution" not in code_to_write:
            code_to_write = code_to_write.replace("class Solution", "public class Solution")

    solution_file = os.path.join(work_dir, "Solution.java")
    with open(solution_file, "w", encoding="utf-8") as f:
        f.write(code_to_write)

    import re
    is_void = bool(re.search(r'\bvoid\s+' + re.escape(function_name) + r'\s*\(', code))

    # Build TestRunner main invocations
    invocations = []
    for idx, t in enumerate(tests):
        raw_args = t.get("args", [])
        var_decls = []
        var_names = []
        for i, a in enumerate(raw_args):
            hint = type_hints[i] if i < len(type_hints) else None
            lit = to_java_literal(a, hint)
            vname = f"arg_{idx}_{i}"
            var_decls.append(f"            var {vname} = {lit};")
            var_names.append(vname)

        decls_str = "\n".join(var_decls)
        args_str = ", ".join(var_names)

        if is_void and var_names:
            call_block = f"""
            long t0 = System.nanoTime();
            sol.{function_name}({args_str});
            long t1 = System.nanoTime();
            double ms = (t1 - t0) / 1000000.0;
            System.out.println("TEST_RES:{idx}:" + ms + ":" + serialize({var_names[0]}));
"""
        else:
            call_block = f"""
            long t0 = System.nanoTime();
            var out{idx} = sol.{function_name}({args_str});
            long t1 = System.nanoTime();
            double ms = (t1 - t0) / 1000000.0;
            System.out.println("TEST_RES:{idx}:" + ms + ":" + serialize(out{idx}));
"""

        invocations.append(f"""
        try {{
{decls_str}
{call_block}
        }} catch (Throwable e) {{
            System.out.println("TEST_ERR:{idx}:" + e.toString());
        }}
""")

    harness_code = HARNESS_TEMPLATE.replace("TEST_INVOCATIONS", "\n".join(invocations))
    harness_file = os.path.join(work_dir, "Harness.java")
    with open(harness_file, "w", encoding="utf-8") as f:
        f.write(harness_code)

    # Compile with javac
    compile_proc = subprocess.run(
        ["javac", "-d", work_dir, solution_file, harness_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=10.0,
    )

    if compile_proc.returncode != 0:
        print(
            json.dumps(
                {
                    "status": "compilation_error",
                    "compile_error": compile_proc.stderr or compile_proc.stdout,
                    "results": [],
                }
            )
        )
        return

    # Run with java
    run_proc = subprocess.run(
        ["java", "-cp", work_dir, "Harness"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=10.0,
    )

    stdout_lines = run_proc.stdout.splitlines()
    stderr_str = run_proc.stderr

    results = []
    all_passed = True

    # Parse TEST_RES / TEST_ERR lines
    test_outputs = {}
    for line in stdout_lines:
        line = line.strip()
        if line.startswith("TEST_RES:"):
            parts = line.split(":", 3)
            idx = int(parts[1])
            duration_ms = float(parts[2])
            raw_json = parts[3]
            try:
                actual_val = json.loads(raw_json)
            except Exception:
                actual_val = raw_json
            test_outputs[idx] = {"actual": actual_val, "duration_ms": duration_ms, "error": None}
        elif line.startswith("TEST_ERR:"):
            parts = line.split(":", 2)
            idx = int(parts[1])
            err_msg = parts[2]
            test_outputs[idx] = {"actual": None, "duration_ms": 0.0, "error": err_msg}

    for idx, t in enumerate(tests):
        expected = t.get("expected")
        raw_args = t.get("args", [])
        entry = test_outputs.get(idx)

        if not entry:
            all_passed = False
            results.append(
                {
                    "passed": False,
                    "input": raw_args,
                    "expected": expected,
                    "actual": None,
                    "error": "Test did not produce output",
                    "duration_ms": 0.0,
                }
            )
            continue

        actual = entry["actual"]
        err = entry["error"]
        dur = entry["duration_ms"]

        if err is not None:
            passed = False
        else:
            passed = check_equal(actual, expected, checker)

        if not passed:
            all_passed = False

        results.append(
            {
                "passed": passed,
                "input": raw_args,
                "expected": expected,
                "actual": actual,
                "error": err,
                "duration_ms": dur,
            }
        )

    print(
        json.dumps(
            {
                "status": "success" if all_passed else "failed",
                "all_passed": all_passed,
                "results": results,
                "stderr": stderr_str,
            }
        )
    )


if __name__ == "__main__":
    main()
