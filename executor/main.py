import json
import logging
import os
import subprocess
import time
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("executor")

app = FastAPI(title="Intervue Code Executor", version="1.0.0")

MAX_OUTPUT_BYTES = 32 * 1024  # 32KB output cap
DEFAULT_TIMEOUT = 5.0
MAX_RUN_TIMEOUT = 15.0


class TestCase(BaseModel):
    args: List[Any]
    expected: Any


class ExecutionRequest(BaseModel):
    language: str = Field(default="python")
    code: str
    function_name: str = Field(default="solution")
    tests: List[TestCase]
    checker: str = Field(default="exact")
    type_hints: Optional[List[str]] = None
    timeout_seconds: Optional[float] = Field(default=DEFAULT_TIMEOUT)


class TestResult(BaseModel):
    passed: bool
    input: List[Any]
    expected: Any
    actual: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None


class ExecutionResponse(BaseModel):
    status: str  # success, failed, compilation_error, runtime_error, timeout, memory_limit
    all_passed: bool = False
    results: List[TestResult] = []
    stdout: str = ""
    stderr: str = ""
    compile_error: Optional[str] = None
    error: Optional[str] = None


@app.get("/health")
def health_check():
    docker_ok = False
    try:
        res = subprocess.run(["docker", "info"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3.0)
        docker_ok = (res.returncode == 0)
    except Exception:
        docker_ok = False
    return {"status": "ok", "docker_connected": docker_ok}


def truncate(text: str, max_bytes: int = MAX_OUTPUT_BYTES) -> str:
    if len(text.encode("utf-8")) <= max_bytes:
        return text
    truncated = text.encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore")
    return truncated + "\n... [Output truncated after 32KB]"


@app.post("/execute", response_model=ExecutionResponse)
def execute_code(req: ExecutionRequest) -> ExecutionResponse:
    if req.language.lower() != "python":
        raise HTTPException(
            status_code=400,
            detail=f"Language '{req.language}' not supported in Phase 1 (Python only)",
        )

    image_name = "intervue-runner-python:latest"
    timeout = min(req.timeout_seconds or DEFAULT_TIMEOUT, MAX_RUN_TIMEOUT)

    payload_dict = {
        "code": req.code,
        "function_name": req.function_name,
        "tests": [t.model_dump() for t in req.tests],
        "checker": req.checker,
        "type_hints": req.type_hints or [],
    }
    payload_bytes = json.dumps(payload_dict).encode("utf-8")

    # Command implementing all requirements from Section 7:
    # --network none, --read-only, tmpfs /tmp, --cap-drop ALL,
    # --security-opt no-new-privileges, non-root user (1000:1000),
    # --pids-limit 64, mem limit 256MB, CPU limit 1
    container_name = f"intervue_run_{int(time.time() * 1000)}"
    cmd = [
        "docker", "run", "-i", "--rm",
        "--name", container_name,
        "--network", "none",
        "--read-only",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--user", "1000:1000",
        "--pids-limit", "64",
        "--memory", "256m",
        "--memory-swap", "256m",
        "--cpus", "1.0",
        image_name,
    ]

    proc = None
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        stdout_raw, stderr_raw = proc.communicate(input=payload_bytes, timeout=timeout)
        exit_code = proc.returncode

        stdout_clean = truncate(stdout_raw.decode("utf-8", errors="replace"))
        stderr_clean = truncate(stderr_raw.decode("utf-8", errors="replace"))

        if exit_code == 137:
            return ExecutionResponse(
                status="memory_limit",
                all_passed=False,
                error="Process killed: memory limit exceeded (256MB)",
                stdout=stdout_clean,
                stderr=stderr_clean,
            )

        # Parse harness output
        lines = stdout_clean.strip().splitlines()
        parsed_data = None
        for line in reversed(lines):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    parsed_data = json.loads(line)
                    break
                except Exception:
                    continue

        if not parsed_data:
            status = "runtime_error" if exit_code != 0 else "failed"
            return ExecutionResponse(
                status=status,
                all_passed=False,
                stdout=stdout_clean,
                stderr=stderr_clean,
                error=stderr_clean or f"Harness exited with code {exit_code}",
            )

        status = parsed_data.get("status", "failed")
        all_passed = parsed_data.get("all_passed", False)
        raw_results = parsed_data.get("results", [])
        compile_err = parsed_data.get("compile_error")

        results = [TestResult(**r) for r in raw_results]

        return ExecutionResponse(
            status=status,
            all_passed=all_passed,
            results=results,
            stdout=stdout_clean,
            stderr=stderr_clean,
            compile_error=compile_err,
            error=parsed_data.get("error"),
        )

    except subprocess.TimeoutExpired:
        if proc:
            proc.kill()
        subprocess.run(["docker", "rm", "-f", container_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return ExecutionResponse(
            status="timeout",
            all_passed=False,
            error=f"Execution timed out after {timeout:.1f}s",
        )
    except Exception as e:
        logger.exception("Execution error")
        return ExecutionResponse(
            status="runtime_error",
            all_passed=False,
            error=str(e),
        )
    finally:
        # Guarantee container removal
        try:
            subprocess.run(["docker", "rm", "-f", container_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
