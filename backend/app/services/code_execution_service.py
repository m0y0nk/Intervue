import logging
from typing import Any, Dict, List, Optional
import httpx
from ..config import settings
from ..schemas.session import RunCodeResponse, RunTestResultItem

logger = logging.getLogger("execution_service")


class CodeExecutionService:
    def __init__(self, executor_url: Optional[str] = None):
        self.executor_url = executor_url or settings.EXECUTOR_URL

    async def execute(
        self,
        code: str,
        function_name: str,
        tests: List[Dict[str, Any]],
        language: str = "python",
        checker: str = "exact",
        type_hints: Optional[List[str]] = None,
        timeout_seconds: float = 5.0,
    ) -> RunCodeResponse:
        payload = {
            "language": language,
            "code": code,
            "function_name": function_name,
            "tests": tests,
            "checker": checker,
            "type_hints": type_hints or [],
            "timeout_seconds": timeout_seconds,
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                resp = await client.post(f"{self.executor_url}/execute", json=payload)
                if resp.status_code != 200:
                    logger.error(f"Executor error {resp.status_code}: {resp.text}")
                    return RunCodeResponse(
                        status="runtime_error",
                        all_passed=False,
                        results=[],
                        error=f"Executor failed with code {resp.status_code}: {resp.text}",
                    )
                data = resp.json()
                results = [RunTestResultItem(**r) for r in data.get("results", [])]
                return RunCodeResponse(
                    status=data.get("status", "failed"),
                    all_passed=data.get("all_passed", False),
                    results=results,
                    stdout=data.get("stdout", ""),
                    stderr=data.get("stderr", ""),
                    compile_error=data.get("compile_error"),
                    error=data.get("error"),
                )
            except (httpx.ConnectError, httpx.RequestError) as e:
                logger.info(f"Executor HTTP service not reachable ({e}); attempting in-process execution fallback...")
                try:
                    import sys
                    import os
                    executor_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "executor"))
                    if executor_dir not in sys.path:
                        sys.path.insert(0, executor_dir)
                    from main import execute_code, ExecutionRequest, TestCase

                    exec_req = ExecutionRequest(
                        language=language,
                        code=code,
                        function_name=function_name,
                        tests=[TestCase(**t) for t in tests],
                        checker=checker,
                        type_hints=type_hints,
                        timeout_seconds=timeout_seconds,
                    )
                    data = execute_code(exec_req)
                    return RunCodeResponse(
                        status=data.status,
                        all_passed=data.all_passed,
                        results=[RunTestResultItem(**r.model_dump()) for r in data.results],
                        stdout=data.stdout,
                        stderr=data.stderr,
                        compile_error=data.compile_error,
                        error=data.error,
                    )
                except Exception as fallback_err:
                    logger.exception("Fallback execution failed")
                    return RunCodeResponse(
                        status="runtime_error",
                        all_passed=False,
                        results=[],
                        error=f"Execution failed: {fallback_err}",
                    )
            except Exception as e:
                logger.exception("Error contacting executor")
                return RunCodeResponse(
                    status="runtime_error",
                    all_passed=False,
                    results=[],
                    error=f"Could not connect to code executor: {str(e)}",
                )


code_execution_service = CodeExecutionService()
