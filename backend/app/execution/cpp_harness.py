#!/usr/bin/env python3
"""
C++ execution harness for AI Technical Interview Simulator.
Compiles candidate code and dynamic harness in sandbox /tmp with g++ -O2 -std=c++20,
executes test cases, validates results, and outputs structured JSON to stdout.
"""

import sys
import json
import time
import math
import os
import subprocess
from typing import Any, List, Optional


def escape_cpp_string(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r") + '"'


def to_cpp_literal(val: Any, type_hint: Optional[str] = None) -> str:
    if val is None:
        return "nullptr"

    if type_hint == "ListNode" or (isinstance(val, list) and type_hint == "ListNode"):
        inner = ", ".join(str(x) for x in val)
        return f"buildList(std::vector<int>{{{inner}}})"

    if type_hint == "TreeNode" or (isinstance(val, list) and type_hint == "TreeNode"):
        items = []
        for x in val:
            if x is None:
                items.append("std::nullopt")
            else:
                items.append(f"std::make_optional<int>({x})")
        inner = ", ".join(items)
        return f"buildTree(std::vector<std::optional<int>>{{{inner}}})"

    if isinstance(val, bool):
        return "true" if val else "false"

    if isinstance(val, (int, float)):
        if type_hint == "double":
            return f"{float(val)}"
        if type_hint == "long" and isinstance(val, int):
            return f"{val}LL"
        return str(val)

    if isinstance(val, str):
        return f"std::string({escape_cpp_string(val)})"

    if isinstance(val, list):
        if not val:
            if type_hint == "int[][]":
                return "std::vector<std::vector<int>>{}"
            if type_hint == "string[]":
                return "std::vector<std::string>{}"
            return "std::vector<int>{}"

        # 2D array
        if isinstance(val[0], list):
            rows = ", ".join("{" + ", ".join(str(x) for x in row) + "}" for row in val)
            return f"std::vector<std::vector<int>>{{{rows}}}"

        # String array
        if isinstance(val[0], str) or type_hint == "string[]":
            items = ", ".join(f"std::string({escape_cpp_string(str(x))})" for x in val)
            return f"std::vector<std::string>{{{items}}}"

        # 1D int array
        items = ", ".join(str(x) for x in val)
        return f"std::vector<int>{{{items}}}"

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
#include <iostream>
#include <vector>
#include <string>
#include <sstream>
#include <queue>
#include <unordered_set>
#include <optional>
#include <chrono>
#include <cmath>
#include <type_traits>

struct ListNode {
    int val;
    ListNode *next;
    ListNode() : val(0), next(nullptr) {}
    ListNode(int x) : val(x), next(nullptr) {}
    ListNode(int x, ListNode *next) : val(x), next(next) {}
};

struct TreeNode {
    int val;
    TreeNode *left;
    TreeNode *right;
    TreeNode() : val(0), left(nullptr), right(nullptr) {}
    TreeNode(int x) : val(x), left(nullptr), right(nullptr) {}
    TreeNode(int x, TreeNode *left, TreeNode *right) : val(x), left(left), right(right) {}
};

static ListNode* buildList(const std::vector<int>& vals) {
    if (vals.empty()) return nullptr;
    ListNode dummy(0);
    ListNode* curr = &dummy;
    for (int v : vals) {
        curr->next = new ListNode(v);
        curr = curr->next;
    }
    return dummy.next;
}

static TreeNode* buildTree(const std::vector<std::optional<int>>& vals) {
    if (vals.empty() || !vals[0].has_value()) return nullptr;
    TreeNode* root = new TreeNode(vals[0].value());
    std::queue<TreeNode*> q;
    q.push(root);
    size_t i = 1;
    while (!q.empty() && i < vals.size()) {
        TreeNode* curr = q.front();
        q.pop();
        if (i < vals.size() && vals[i].has_value()) {
            curr->left = new TreeNode(vals[i].value());
            q.push(curr->left);
        }
        i++;
        if (i < vals.size() && vals[i].has_value()) {
            curr->right = new TreeNode(vals[i].value());
            q.push(curr->right);
        }
        i++;
    }
    return root;
}

// Serialization overloads
static std::string serialize(bool val) { return val ? "true" : "false"; }
static std::string serialize(int val) { return std::to_string(val); }
static std::string serialize(long long val) { return std::to_string(val); }
static std::string serialize(double val) { return std::to_string(val); }
static std::string serialize(const std::string& val) {
    std::ostringstream ss;
    ss << "\\"";
    for (char c : val) {
        if (c == '\\\\') ss << "\\\\\\\\";
        else if (c == '"') ss << "\\\\\\"";
        else if (c == '\\n') ss << "\\\\n";
        else ss << c;
    }
    ss << "\\"";
    return ss.str();
}

static std::string serialize(const std::vector<int>& vec) {
    std::ostringstream ss;
    ss << "[";
    for (size_t i = 0; i < vec.size(); i++) {
        if (i > 0) ss << ", ";
        ss << vec[i];
    }
    ss << "]";
    return ss.str();
}

static std::string serialize(const std::vector<std::vector<int>>& mat) {
    std::ostringstream ss;
    ss << "[";
    for (size_t i = 0; i < mat.size(); i++) {
        if (i > 0) ss << ", ";
        ss << serialize(mat[i]);
    }
    ss << "]";
    return ss.str();
}

static std::string serialize(const std::vector<std::string>& vec) {
    std::ostringstream ss;
    ss << "[";
    for (size_t i = 0; i < vec.size(); i++) {
        if (i > 0) ss << ", ";
        ss << serialize(vec[i]);
    }
    ss << "]";
    return ss.str();
}

static std::string serialize(ListNode* head) {
    std::ostringstream ss;
    ss << "[";
    ListNode* curr = head;
    std::unordered_set<ListNode*> seen;
    int count = 0;
    while (curr != nullptr && count < 10000) {
        if (seen.count(curr)) break;
        seen.insert(curr);
        if (count > 0) ss << ", ";
        ss << curr->val;
        curr = curr->next;
        count++;
    }
    ss << "]";
    return ss.str();
}

static std::string serialize(TreeNode* root) {
    if (!root) return "[]";
    std::vector<std::string> list;
    std::queue<TreeNode*> q;
    q.push(root);
    while (!q.empty()) {
        TreeNode* curr = q.front();
        q.pop();
        if (curr) {
            list.push_back(std::to_string(curr->val));
            q.push(curr->left);
            q.push(curr->right);
        } else {
            list.push_back("null");
        }
    }
    while (!list.empty() && list.back() == "null") {
        list.pop_back();
    }
    std::ostringstream ss;
    ss << "[";
    for (size_t i = 0; i < list.size(); i++) {
        if (i > 0) ss << ", ";
        ss << list[i];
    }
    ss << "]";
    return ss.str();
}

// User candidate code
USER_CODE_PLACEHOLDER

int main() {
    Solution sol;
    TEST_INVOCATIONS
    return 0;
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

    # Wrap in class Solution if user wrote standalone function
    if "class Solution" not in code:
        code_to_write = f"class Solution {{\npublic:\n{code}\n}};\n"
    else:
        code_to_write = code

    import re
    is_void = bool(re.search(r'\bvoid\s+' + re.escape(function_name) + r'\s*\(', code))

    # Build test invocations
    invocations = []
    for idx, t in enumerate(tests):
        raw_args = t.get("args", [])
        var_decls = []
        var_names = []
        for i, a in enumerate(raw_args):
            hint = type_hints[i] if i < len(type_hints) else None
            lit = to_cpp_literal(a, hint)
            var_name = f"arg_{idx}_{i}"
            var_decls.append(f"        auto {var_name} = {lit};")
            var_names.append(var_name)

        decls_str = "\n".join(var_decls)
        args_str = ", ".join(var_names)
        if var_names:
            out_target = f"serialize({var_names[0]})"
        else:
            out_target = '""'

        if is_void:
            call_block = f"""
        auto t0 = std::chrono::high_resolution_clock::now();
        sol.{function_name}({args_str});
        auto t1 = std::chrono::high_resolution_clock::now();
        double ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
        std::cout << "TEST_RES:{idx}:" << ms << ":" << {out_target} << std::endl;
"""
        else:
            call_block = f"""
        auto t0 = std::chrono::high_resolution_clock::now();
        auto out{idx} = sol.{function_name}({args_str});
        auto t1 = std::chrono::high_resolution_clock::now();
        double ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
        std::cout << "TEST_RES:{idx}:" << ms << ":" << serialize(out{idx}) << std::endl;
"""

        invocations.append(f"""
    try {{
{decls_str}
{call_block}
    }} catch (const std::exception& e) {{
        std::cout << "TEST_ERR:{idx}:" << e.what() << std::endl;
    }} catch (...) {{
        std::cout << "TEST_ERR:{idx}:UnknownException" << std::endl;
    }}
""")

    source_code = HARNESS_TEMPLATE.replace("USER_CODE_PLACEHOLDER", code_to_write).replace(
        "TEST_INVOCATIONS", "\n".join(invocations)
    )

    cpp_file = os.path.join(work_dir, "harness.cpp")
    bin_file = os.path.join(work_dir, "solution_bin")

    with open(cpp_file, "w", encoding="utf-8") as f:
        f.write(source_code)

    # Compile with g++ -O2 -std=c++20
    compile_proc = subprocess.run(
        ["g++", "-O2", "-std=c++20", cpp_file, "-o", bin_file],
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

    # Run binary
    run_proc = subprocess.run(
        [bin_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=10.0,
    )

    stdout_lines = run_proc.stdout.splitlines()
    stderr_str = run_proc.stderr

    results = []
    all_passed = True

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
