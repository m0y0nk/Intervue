from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FunctionArg(BaseModel):
    name: str
    type: str  # int, long, double, bool, string, int[], int[][], string[], ListNode, TreeNode


class FunctionSignature(BaseModel):
    function_name: str
    args: List[FunctionArg]
    return_type: str


def generate_starter_templates(sig: FunctionSignature) -> Dict[str, str]:
    fn_name = sig.function_name
    raw_args = sig.args
    ret_type = sig.return_type.strip()

    # 1. Python mapping
    py_type_map = {
        "int": "int",
        "long": "int",
        "double": "float",
        "float": "float",
        "bool": "bool",
        "boolean": "bool",
        "string": "str",
        "str": "str",
        "int[]": "list[int]",
        "int[][]": "list[list[int]]",
        "string[]": "list[str]",
        "ListNode": "Optional[ListNode]",
        "TreeNode": "Optional[TreeNode]",
        "void": "None",
    }
    py_args = [f"{a.name}: {py_type_map.get(a.type, 'Any')}" for a in raw_args]
    py_args_str = ", ".join(py_args)
    py_ret = py_type_map.get(ret_type, "Any")
    
    python_template = f'''# Definition for singly-linked list:
# class ListNode:
#     def __init__(self, val=0, next=None):
#         self.val = val
#         self.next = next
#
# Definition for a binary tree node:
# class TreeNode:
#     def __init__(self, val=0, left=None, right=None):
#         self.val = val
#         self.left = left
#         self.right = right

def {fn_name}({py_args_str}) -> {py_ret}:
    # Write your solution here
    pass
'''

    # 2. Java mapping
    java_type_map = {
        "int": "int",
        "long": "long",
        "double": "double",
        "float": "double",
        "bool": "boolean",
        "boolean": "boolean",
        "string": "String",
        "str": "String",
        "int[]": "int[]",
        "int[][]": "int[][]",
        "string[]": "String[]",
        "ListNode": "ListNode",
        "TreeNode": "TreeNode",
        "void": "void",
    }
    java_default_ret = {
        "void": "// In-place modification, no return needed",
        "int": "return 0;",
        "long": "return 0L;",
        "double": "return 0.0;",
        "boolean": "return false;",
        "String": 'return "";',
        "int[]": "return new int[]{};",
        "int[][]": "return new int[][]{};",
        "String[]": "return new String[]{};",
        "ListNode": "return null;",
        "TreeNode": "return null;",
    }
    java_ret = java_type_map.get(ret_type, "void")
    java_args = [f"{java_type_map.get(a.type, 'Object')} {a.name}" for a in raw_args]
    java_args_str = ", ".join(java_args)
    java_ret_stmt = java_default_ret.get(java_ret, "return null;")

    java_template = f'''import java.util.*;

/**
 * Definition for singly-linked list:
 * public class ListNode {{
 *     int val;
 *     ListNode next;
 *     ListNode() {{}}
 *     ListNode(int val) {{ this.val = val; }}
 *     ListNode(int val, ListNode next) {{ this.val = val; this.next = next; }}
 * }}
 * 
 * Definition for a binary tree node:
 * public class TreeNode {{
 *     int val;
 *     TreeNode left;
 *     TreeNode right;
 *     TreeNode() {{}}
 *     TreeNode(int val) {{ this.val = val; }}
 *     TreeNode(int val, TreeNode left, TreeNode right) {{
 *         this.val = val;
 *         this.left = left;
 *         this.right = right;
 *     }}
 * }}
 */
public class Solution {{
    public {java_ret} {fn_name}({java_args_str}) {{
        // Write your solution here
        {java_ret_stmt}
    }}
}}
'''

    # 3. C++ mapping
    cpp_type_map = {
        "int": "int",
        "long": "long long",
        "double": "double",
        "float": "double",
        "bool": "bool",
        "boolean": "bool",
        "string": "std::string",
        "str": "std::string",
        "int[]": "std::vector<int>&",
        "int[][]": "std::vector<std::vector<int>>&",
        "string[]": "std::vector<std::string>&",
        "ListNode": "ListNode*",
        "TreeNode": "TreeNode*",
        "void": "void",
    }
    cpp_ret_type_map = {
        "int": "int",
        "long": "long long",
        "double": "double",
        "float": "double",
        "bool": "bool",
        "boolean": "bool",
        "string": "std::string",
        "str": "std::string",
        "int[]": "std::vector<int>",
        "int[][]": "std::vector<std::vector<int>>",
        "string[]": "std::vector<std::string>",
        "ListNode": "ListNode*",
        "TreeNode": "TreeNode*",
        "void": "void",
    }
    cpp_default_ret = {
        "void": "// In-place modification, no return needed",
        "int": "return 0;",
        "long long": "return 0;",
        "double": "return 0.0;",
        "bool": "return false;",
        "std::string": 'return "";',
        "std::vector<int>": "return {};",
        "std::vector<std::vector<int>>": "return {};",
        "std::vector<std::string>": "return {};",
        "ListNode*": "return nullptr;",
        "TreeNode*": "return nullptr;",
    }
    cpp_ret = cpp_ret_type_map.get(ret_type, "void")
    cpp_args = [f"{cpp_type_map.get(a.type, 'auto')} {a.name}" for a in raw_args]
    cpp_args_str = ", ".join(cpp_args)
    cpp_ret_stmt = cpp_default_ret.get(cpp_ret, "return {};")

    cpp_template = f'''#include <iostream>
#include <vector>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <algorithm>
#include <queue>

/**
 * Definition for singly-linked list:
 * struct ListNode {{
 *     int val;
 *     ListNode *next;
 *     ListNode() : val(0), next(nullptr) {{}}
 *     ListNode(int x) : val(x), next(nullptr) {{}}
 *     ListNode(int x, ListNode *next) : val(x), next(next) {{}}
 * }};
 * 
 * Definition for a binary tree node:
 * struct TreeNode {{
 *     int val;
 *     TreeNode *left;
 *     TreeNode *right;
 *     TreeNode() : val(0), left(nullptr), right(nullptr) {{}}
 *     TreeNode(int x) : val(x), left(nullptr), right(nullptr) {{}}
 *     TreeNode(int x, TreeNode *left, TreeNode *right) : val(x), left(left), right(right) {{}}
 * }};
 */
class Solution {{
public:
    {cpp_ret} {fn_name}({cpp_args_str}) {{
        // Write your solution here
        {cpp_ret_stmt}
    }}
}};
'''

    return {
        "python": python_template,
        "java": java_template,
        "cpp": cpp_template,
    }


class ProblemExample(BaseModel):
    input_str: str
    output_str: str
    explanation: Optional[str] = None


class TestCaseSchema(BaseModel):
    args: List[Any]
    expected: Any


class ProblemPublic(BaseModel):
    id: str
    title: str
    statement: str
    examples: List[ProblemExample]
    signature: FunctionSignature
    revealed_constraints: List[str] = Field(default_factory=list)
    visible_tests: List[TestCaseSchema] = Field(default_factory=list)
    starter_code: Dict[str, str] = Field(default_factory=dict)  # language -> template
    checker: str = Field(default="exact")  # exact | unordered | float_tolerance(eps)
    category: Optional[str] = None
    difficulty: Optional[str] = None


class ProblemPublicBlind(BaseModel):
    statement: str
    examples: List[ProblemExample]
    signature: FunctionSignature
    revealed_constraints: List[str] = Field(default_factory=list)
    visible_tests: List[TestCaseSchema] = Field(default_factory=list)
    starter_code: Dict[str, str] = Field(default_factory=dict)
    checker: str = Field(default="exact")


class RubricItem(BaseModel):
    dimension: str
    criteria: str
    weight: float = 1.0


class ProblemPrivate(ProblemPublic):
    """
    CRITICAL ISOLATION:
    Only evaluation_service and problem_validator may import ProblemPrivate.
    Interviewer routes, interviewer service and all frontend-facing schemas
    must import ProblemPublic or ProblemPublicBlind only.
    """
    categories: List[str] = Field(default_factory=list)
    difficulty: str = "medium"
    brute_force_approach: str = ""
    optimal_approach: str = ""
    alternative_approaches: List[str] = Field(default_factory=list)
    expected_time_complexity: str = ""
    expected_space_complexity: str = ""
    python_reference: str = ""
    python_brute_force: str = ""
    input_generator: str = ""  # python snippet generating list of test args
    hidden_tests: List[TestCaseSchema] = Field(default_factory=list)
    edge_cases: List[str] = Field(default_factory=list)
    rubric: List[RubricItem] = Field(default_factory=list)
    fingerprint: Optional[str] = None
