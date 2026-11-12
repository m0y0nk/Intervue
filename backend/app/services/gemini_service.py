import asyncio
import json
import logging
import os
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel
from ..config import settings

logger = logging.getLogger("gemini_service")

T = TypeVar("T", bound=BaseModel)


def _sanitize_schema_for_gemini(schema: Any) -> Any:
    """
    Recursively removes additionalProperties from JSON schemas.
    Gemini Developer API strictly rejects schemas containing additionalProperties.
    """
    if isinstance(schema, dict):
        return {
            k: _sanitize_schema_for_gemini(v)
            for k, v in schema.items()
            if k != "additionalProperties"
        }
    elif isinstance(schema, list):
        return [_sanitize_schema_for_gemini(item) for item in schema]
    return schema


class GeminiService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL
        self.client = None

        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                logger.info(f"Gemini client initialized with model {self.model_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize google-genai client: {e}")
                self.client = None

    def is_configured(self) -> bool:
        return self.client is not None

    async def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        temperature: float = 0.2,
        system_instruction: Optional[str] = None,
    ) -> T:
        """Calls Gemini with structured output, or falls back to mock if not configured."""
        if not self.is_configured():
            logger.info("Gemini not configured; generating schema-compliant mock response.")
            return self._mock_response(prompt, response_schema)

        # Prepare schema for Gemini Developer API (strips additionalProperties)
        gemini_schema: Any = response_schema
        if isinstance(response_schema, type) and issubclass(response_schema, BaseModel):
            raw_schema = response_schema.model_json_schema()
            gemini_schema = _sanitize_schema_for_gemini(raw_schema)

        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                from google.genai import types
                config = types.GenerateContentConfig(
                    temperature=temperature,
                    response_mime_type="application/json",
                    response_schema=gemini_schema,
                    system_instruction=system_instruction,
                )
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config,
                )
                data = json.loads(response.text)
                return response_schema.model_validate(data)
            except Exception as e:
                err_str = str(e)
                is_transient = any(code in err_str for code in ["503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "high demand"])
                if is_transient and attempt < max_retries:
                    wait_sec = 1.5 * (attempt + 1)
                    logger.warning(f"Gemini {self.model_name} transient error ({e}); retrying in {wait_sec}s...")
                    await asyncio.sleep(wait_sec)
                    continue
                logger.warning(f"Gemini call with model '{self.model_name}' failed ({e}); falling back to mock response.")
                return self._mock_response(prompt, response_schema)

    async def generate_free_text(
        self,
        prompt: str,
        temperature: float = 0.4,
        system_instruction: Optional[str] = None,
    ) -> Optional[str]:
        """
        Generates unstructured free text from Gemini.
        Returns None on failure (caller should handle gracefully).
        Never raises — always returns str or None.
        """
        if not self.is_configured():
            logger.info("Gemini not configured; skipping free-text generation.")
            return None

        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                from google.genai import types
                config = types.GenerateContentConfig(
                    temperature=temperature,
                    system_instruction=system_instruction,
                )
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config,
                )
                return response.text.strip() if response.text else None
            except Exception as e:
                err_str = str(e)
                is_transient = any(code in err_str for code in ["503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "high demand"])
                if is_transient and attempt < max_retries:
                    wait_sec = 1.5 * (attempt + 1)
                    logger.warning(f"Gemini free-text {self.model_name} transient error ({e}); retrying in {wait_sec}s...")
                    await asyncio.sleep(wait_sec)
                    continue
                logger.warning(f"Gemini free-text call on '{self.model_name}' failed ({e}).")
                return None

    def _mock_response(self, prompt: str, schema: Type[T]) -> T:
        """Produces realistic mock data satisfying Pydantic schema validation."""
        schema_name = schema.__name__

        if schema_name == "ProblemPrivate":
            p_lower = prompt.lower()
            if "ai_business" in p_lower or "business" in p_lower or "order" in p_lower or "logistic" in p_lower:
                return schema(
                    id="prob_business_shipping_01",
                    title="Order Batch Shipping Optimization",
                    statement="An e-commerce distribution center packs customer orders into shipping containers. Each container has a maximum weight limit, and each trip can transport at most two packages. Given an array of package weights and the weight limit, calculate the minimum number of shipping containers needed to transport all packages.",
                    examples=[
                        {"input_str": "weights = [1, 2], limit = 3", "output_str": "1", "explanation": "Both packages can fit in a single container (1 + 2 = 3)."},
                        {"input_str": "weights = [3, 2, 2, 1], limit = 3", "output_str": "3", "explanation": "Trip 1: [3], Trip 2: [2, 1], Trip 3: [2]."},
                        {"input_str": "weights = [3, 5, 3, 4], limit = 5", "output_str": "4", "explanation": "Each container carries at most one heavy package: [5], [3], [3], [4]."},
                    ],
                    signature={
                        "function_name": "min_shipping_containers",
                        "args": [
                            {"name": "weights", "type": "int[]"},
                            {"name": "limit", "type": "int"},
                        ],
                        "return_type": "int",
                    },
                    revealed_constraints=[
                        "1 <= weights.length <= 50000",
                        "1 <= weights[i] <= limit <= 30000",
                    ],
                    visible_tests=[
                        {"args": [[1, 2], 3], "expected": 1},
                        {"args": [[3, 2, 2, 1], 3], "expected": 3},
                    ],
                    starter_code={
                        "python": "def min_shipping_containers(weights: list[int], limit: int) -> int:\n    # Write your solution here\n    pass\n",
                    },
                    checker="exact",
                    category="greedy",
                    difficulty="medium",
                    categories=["greedy", "two_pointers"],
                    brute_force_approach="Try all combinations of package pairings to find minimal containers.",
                    optimal_approach="Sort packages by weight, then use two pointers greedily pairing lightest with heaviest.",
                    alternative_approaches=["Frequency bucket counting with greedy pairing."],
                    expected_time_complexity="O(N log N)",
                    expected_space_complexity="O(1)",
                    python_reference="""def min_shipping_containers(weights, limit):
    w = sorted(weights)
    left, right = 0, len(w) - 1
    containers = 0
    while left <= right:
        if left == right:
            containers += 1
            break
        if w[left] + w[right] <= limit:
            left += 1
        right -= 1
        containers += 1
    return containers
""",
                    python_brute_force="""def min_shipping_containers(weights, limit):
    w = sorted(weights)
    i, j = 0, len(w) - 1
    ans = 0
    while i <= j:
        if i == j:
            ans += 1
            break
        if w[i] + w[j] <= limit:
            i += 1
        j -= 1
        ans += 1
    return ans
""",
                    input_generator="""import random
def generate_inputs(n=100):
    tests = []
    for _ in range(n):
        l = random.randint(10, 50)
        sz = random.randint(2, 25)
        w = [random.randint(1, l) for _ in range(sz)]
        tests.append([w, l])
    return tests
""",
                    hidden_tests=[
                        {"args": [[3, 5, 3, 4], 5], "expected": 4},
                        {"args": [[2, 4], 5], "expected": 2},
                        {"args": [[5], 10], "expected": 1},
                        {"args": [[1, 2, 2, 3], 3], "expected": 3},
                    ],
                    edge_cases=["Single package", "All packages equal limit", "All packages weight 1"],
                    rubric=[
                        {"dimension": "Problem Understanding", "criteria": "Clarified that at most 2 packages fit in one container", "weight": 1.0},
                        {"dimension": "Optimal Approach", "criteria": "Identified two-pointer greedy approach after sorting", "weight": 1.5},
                    ],
                    fingerprint="business_shipping_greedy_01",
                )

            if "binary_search" in p_lower:
                return schema(
                    id="prob_binsearch_insert_01",
                    title="Search Insert Position",
                    statement="Given a sorted array of distinct integers and a target value, return the index if the target is found. If not, return the index where it would be if it were inserted in order. You must write an algorithm with O(log n) runtime complexity.",
                    examples=[
                        {"input_str": "nums = [1,3,5,6], target = 5", "output_str": "2", "explanation": "5 is found at index 2."},
                        {"input_str": "nums = [1,3,5,6], target = 2", "output_str": "1", "explanation": "2 should be inserted at index 1."},
                        {"input_str": "nums = [1,3,5,6], target = 7", "output_str": "4", "explanation": "7 should be inserted at index 4."},
                    ],
                    signature={
                        "function_name": "search_insert",
                        "args": [
                            {"name": "nums", "type": "int[]"},
                            {"name": "target", "type": "int"},
                        ],
                        "return_type": "int",
                    },
                    revealed_constraints=[
                        "1 <= nums.length <= 10^4",
                        "-10^4 <= nums[i] <= 10^4",
                        "nums contains distinct values sorted in ascending order.",
                        "-10^4 <= target <= 10^4",
                    ],
                    visible_tests=[
                        {"args": [[1, 3, 5, 6], 5], "expected": 2},
                        {"args": [[1, 3, 5, 6], 2], "expected": 1},
                        {"args": [[1, 3, 5, 6], 7], "expected": 4},
                    ],
                    starter_code={
                        "python": "def search_insert(nums: list[int], target: int) -> int:\n    # Write your solution here\n    pass\n",
                    },
                    checker="exact",
                    category="binary_search",
                    difficulty="easy",
                    categories=["binary_search"],
                    brute_force_approach="Scan array linearly until finding an element >= target in O(N).",
                    optimal_approach="Use binary search maintaining left and right pointers to locate index in O(log N).",
                    alternative_approaches=["Linear search O(N)."],
                    expected_time_complexity="O(log N)",
                    expected_space_complexity="O(1)",
                    python_reference="""def search_insert(nums, target):
    l, r = 0, len(nums) - 1
    while l <= r:
        m = (l + r) // 2
        if nums[m] == target:
            return m
        elif nums[m] < target:
            l = m + 1
        else:
            r = m - 1
    return l
""",
                    python_brute_force="""def search_insert(nums, target):
    for i, x in enumerate(nums):
        if x >= target:
            return i
    return len(nums)
""",
                    input_generator="""import random
def generate_inputs(n=100):
    tests = []
    for _ in range(n):
        sz = random.randint(1, 20)
        nums = sorted(list(set(random.randint(-50, 50) for _ in range(sz))))
        target = random.randint(-60, 60)
        tests.append([nums, target])
    return tests
""",
                    hidden_tests=[
                        {"args": [[1, 3, 5, 6], 0], "expected": 0},
                        {"args": [[1], 1], "expected": 0},
                        {"args": [[1, 3], 2], "expected": 1},
                        {"args": [[2, 5], 1], "expected": 0},
                    ],
                    edge_cases=["Target smaller than all elements", "Target larger than all elements", "Single element array"],
                    rubric=[
                        {"dimension": "Problem Understanding", "criteria": "Clarified strictly increasing sorted assumption", "weight": 1.0},
                        {"dimension": "Optimal Approach", "criteria": "Identified O(log N) binary search boundary condition", "weight": 1.5},
                    ],
                    fingerprint="binsearch_search_insert_01",
                )

            if "dynamic_programming" in p_lower or "dp" in p_lower:
                return schema(
                    id="prob_dp_house_robber_01",
                    title="Maximum Vault Extraction",
                    statement="You are planning to extract funds from a sequence of security vaults along a street. Each vault has a certain amount of cash stashed. Adjacent vaults have connected security alarms and will automatically alert law enforcement if two adjacent vaults are accessed on the same night. Given an integer array representing the amount of money in each vault, return the maximum amount of money you can extract without alerting security.",
                    examples=[
                        {"input_str": "nums = [1, 2, 3, 1]", "output_str": "4", "explanation": "Rob vault 1 (money = 1) and vault 3 (money = 3). Total = 4."},
                        {"input_str": "nums = [2, 7, 9, 3, 1]", "output_str": "12", "explanation": "Rob vault 1 (money = 2), vault 3 (money = 9) and vault 5 (money = 1). Total = 12."},
                        {"input_str": "nums = [2, 1, 1, 2]", "output_str": "4", "explanation": "Rob vault 1 (money = 2) and vault 4 (money = 2). Total = 4."},
                    ],
                    signature={
                        "function_name": "max_vault_extraction",
                        "args": [
                            {"name": "nums", "type": "int[]"},
                        ],
                        "return_type": "int",
                    },
                    revealed_constraints=[
                        "1 <= nums.length <= 100",
                        "0 <= nums[i] <= 400",
                    ],
                    visible_tests=[
                        {"args": [[1, 2, 3, 1]], "expected": 4},
                        {"args": [[2, 7, 9, 3, 1]], "expected": 12},
                        {"args": [[2, 1, 1, 2]], "expected": 4},
                    ],
                    starter_code={
                        "python": "def max_vault_extraction(nums: list[int]) -> int:\n    # Write your solution here\n    pass\n",
                    },
                    checker="exact",
                    category="dynamic_programming",
                    difficulty="medium",
                    categories=["dynamic_programming"],
                    brute_force_approach="Try all valid non-adjacent subsets recursively in O(2^N).",
                    optimal_approach="Use dynamic programming tracking prev1 and prev2 in O(N) time and O(1) space.",
                    alternative_approaches=["Top-down memoization with recursion in O(N) space."],
                    expected_time_complexity="O(N)",
                    expected_space_complexity="O(1)",
                    python_reference="""def max_vault_extraction(nums):
    if not nums:
        return 0
    prev2, prev1 = 0, 0
    for x in nums:
        prev2, prev1 = prev1, max(prev1, prev2 + x)
    return prev1
""",
                    python_brute_force="""def max_vault_extraction(nums):
    def solve(i):
        if i >= len(nums):
            return 0
        return max(nums[i] + solve(i + 2), solve(i + 1))
    return solve(0)
""",
                    input_generator="""import random
def generate_inputs(n=10):
    tests = []
    for _ in range(n):
        sz = random.randint(1, 15)
        tests.append([[random.randint(0, 50) for _ in range(sz)]])
    return tests
""",
                    hidden_tests=[
                        {"args": [[0]], "expected": 0},
                        {"args": [[100]], "expected": 100},
                        {"args": [[5, 1, 1, 5]], "expected": 10},
                        {"args": [[4, 1, 2, 7, 5, 3, 1]], "expected": 14},
                    ],
                    edge_cases=["Single vault", "Empty or zeros", "All vaults have equal value"],
                    rubric=[
                        {"dimension": "Problem Understanding", "criteria": "Clarified that non-adjacent condition is strictly enforced", "weight": 1.0},
                        {"dimension": "Optimal Approach", "criteria": "Identified DP recurrence relation with O(1) memory state", "weight": 1.5},
                    ],
                    fingerprint="dp_house_robber_01",
                )

            # Realistic DSA Problem (Default: Two Sum)
            return schema(
                id="prob_two_sum_01",
                title="Pair Sum Target",
                statement="Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target. You may assume each input has exactly one solution, and you may not use the same element twice.",
                examples=[
                    {
                        "input_str": "nums = [2,7,11,15], target = 9",
                        "output_str": "[0,1]",
                        "explanation": "nums[0] + nums[1] == 9, so we return [0, 1].",
                    },
                    {
                        "input_str": "nums = [3,2,4], target = 6",
                        "output_str": "[1,2]",
                        "explanation": "nums[1] + nums[2] == 6, so we return [1, 2].",
                    },
                    {
                        "input_str": "nums = [3,3], target = 6",
                        "output_str": "[0,1]",
                        "explanation": "nums[0] + nums[1] == 6, so we return [0, 1].",
                    },
                ],
                signature={
                    "function_name": "two_sum",
                    "args": [
                        {"name": "nums", "type": "int[]"},
                        {"name": "target", "type": "int"},
                    ],
                    "return_type": "int[]",
                },
                revealed_constraints=[
                    "2 <= nums.length <= 10^4",
                    "-10^9 <= nums[i] <= 10^9",
                    "-10^9 <= target <= 10^9",
                    "Only one valid answer exists.",
                ],
                visible_tests=[
                    {"args": [[2, 7, 11, 15], 9], "expected": [0, 1]},
                    {"args": [[3, 2, 4], 6], "expected": [1, 2]},
                ],
                starter_code={
                    "python": "def two_sum(nums: list[int], target: int) -> list[int]:\n    # Write your solution here\n    pass\n",
                    "java": """import java.util.*;

public class Solution {
    public int[] twoSum(int[] nums, int target) {
        // Write your solution here
        return new int[]{};
    }
}
""",
                    "cpp": """#include <iostream>
#include <vector>
#include <unordered_map>

class Solution {
public:
    std::vector<int> twoSum(std::vector<int>& nums, int target) {
        // Write your solution here
        return {};
    }
};
""",
                },
                checker="exact",
                category="arrays_hashing",
                difficulty="medium",
                categories=["arrays_hashing"],
                brute_force_approach="Check all pairs (i, j) with nested loops and return indices when sum matches target.",
                optimal_approach="Use a hash map to store value to index mapping. In a single pass, check if target - num exists in map.",
                alternative_approaches=["Sort with original indices and use two pointers (O(N log N))."],
                expected_time_complexity="O(N)",
                expected_space_complexity="O(N)",
                python_reference="""def two_sum(nums, target):
    seen = {}
    for i, x in enumerate(nums):
        diff = target - x
        if diff in seen:
            return [seen[diff], i]
        seen[x] = i
    return []
""",
                python_brute_force="""def two_sum(nums, target):
    n = len(nums)
    for i in range(n):
        for j in range(i + 1, n):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []
""",
                input_generator="""import random
def generate_inputs(n=200):
    tests = []
    for _ in range(n):
        length = random.randint(2, 20)
        nums = [random.randint(-50, 50) for _ in range(length)]
        i, j = random.sample(range(length), 2)
        if i > j:
            i, j = j, i
        target = nums[i] + nums[j]
        tests.append([nums, target])
    return tests
""",
                hidden_tests=[
                    {"args": [[1, 5, 6, 12, 19], 20], "expected": [0, 4]},
                    {"args": [[-3, 4, 3, 90], 0], "expected": [0, 2]},
                    {"args": [[100, 200, 300, 400], 700], "expected": [2, 3]},
                    {"args": [[0, 4, 3, 0], 0], "expected": [0, 3]},
                ],
                edge_cases=["Negative numbers", "Duplicate elements adding up to target", "Zeros"],
                rubric=[
                    {"dimension": "Problem Understanding", "criteria": "Clarified one-solution assumption and negative values", "weight": 1.0},
                    {"dimension": "Optimal Approach", "criteria": "Identified hash map lookup instead of O(N^2) brute force", "weight": 1.5},
                ],
                fingerprint="hash_two_sum_arrays_hashing",
            )

        # Fallback to schema default or empty instantiation
        try:
            return schema()
        except Exception:
            return schema.model_validate({})


gemini_service = GeminiService()
