import json
import logging
import os
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel
from ..config import settings

logger = logging.getLogger("gemini_service")

T = TypeVar("T", bound=BaseModel)


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

        try:
            from google.genai import types
            config = types.GenerateContentConfig(
                temperature=temperature,
                response_mime_type="application/json",
                response_schema=response_schema,
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
            logger.warning(f"Gemini API call failed ({e}); falling back to mock response.")
            return self._mock_response(prompt, response_schema)

    def _mock_response(self, prompt: str, schema: Type[T]) -> T:
        """Produces realistic mock data satisfying Pydantic schema validation."""
        schema_name = schema.__name__

        if schema_name == "ProblemPrivate":
            # Realistic DSA Problem
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
