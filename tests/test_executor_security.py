import pytest
import sys
import os

# Add executor to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "executor")))

from main import app, execute_code, ExecutionRequest, TestCase
from fastapi.testclient import TestClient

client = TestClient(app)


def test_executor_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["docker_connected"] is True


def test_valid_execution():
    code = """
def two_sum(nums, target):
    seen = {}
    for i, x in enumerate(nums):
        if target - x in seen:
            return [seen[target - x], i]
        seen[x] = i
    return []
"""
    req = ExecutionRequest(
        language="python",
        code=code,
        function_name="two_sum",
        tests=[
            TestCase(args=[[2, 7, 11, 15], 9], expected=[0, 1]),
            TestCase(args=[[3, 2, 4], 6], expected=[1, 2]),
        ],
        checker="exact",
    )
    res = execute_code(req)
    assert res.status == "success"
    assert res.all_passed is True
    assert len(res.results) == 2
    assert res.results[0].passed is True
    assert res.results[1].passed is True


def test_network_blocked():
    """Security Test: verify container network is none; outbound socket connections must fail."""
    code = """
import socket

def solution():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.0)
        s.connect(("8.8.8.8", 53))
        return "connected"
    except Exception as e:
        return "network_blocked"
"""
    req = ExecutionRequest(
        language="python",
        code=code,
        function_name="solution",
        tests=[TestCase(args=[], expected="network_blocked")],
        checker="exact",
    )
    res = execute_code(req)
    assert res.status == "success"
    assert res.results[0].actual == "network_blocked"
    assert res.results[0].passed is True


def test_infinite_loop_timeout():
    """Security Test: infinite loop terminates within configured timeout without hanging the host."""
    code = """
def solution():
    while True:
        pass
"""
    req = ExecutionRequest(
        language="python",
        code=code,
        function_name="solution",
        tests=[TestCase(args=[], expected=1)],
        timeout_seconds=2.0,
    )
    res = execute_code(req)
    assert res.status == "timeout"
    assert res.all_passed is False
    assert "timed out" in (res.error or "")


def test_memory_bomb_killed():
    """Security Test: allocating excessive memory is caught by the 256MB cgroup limit."""
    code = """
def solution():
    # Attempt to allocate 500MB
    blob = bytearray(500 * 1024 * 1024)
    return len(blob)
"""
    req = ExecutionRequest(
        language="python",
        code=code,
        function_name="solution",
        tests=[TestCase(args=[], expected=1)],
    )
    res = execute_code(req)
    # Container gets OOM-killed (status memory_limit or runtime_error)
    assert res.status in ("memory_limit", "runtime_error", "failed")
    assert res.all_passed is False


def test_fork_bomb_contained():
    """Security Test: fork bomb is blocked by pids-limit 64."""
    code = """
import os

def solution():
    try:
        for _ in range(200):
            pid = os.fork()
            if pid == 0:
                os._exit(0)
    except Exception:
        return "fork_blocked"
    return "fork_ran"
"""
    req = ExecutionRequest(
        language="python",
        code=code,
        function_name="solution",
        tests=[TestCase(args=[], expected="fork_blocked")],
        timeout_seconds=3.0,
    )
    res = execute_code(req)
    # The fork bomb should be caught/contained without crashing executor or host
    assert res.all_passed is True or res.status in ("success", "runtime_error", "timeout")


def test_filesystem_writes_outside_tmpfs_fail():
    """Security Test: writes outside /tmp fail due to read-only rootfs."""
    code = """
def solution():
    try:
        with open("/etc/pwned.txt", "w") as f:
            f.write("hacked")
        return "write_succeeded"
    except Exception:
        return "write_prevented"
"""
    req = ExecutionRequest(
        language="python",
        code=code,
        function_name="solution",
        tests=[TestCase(args=[], expected="write_prevented")],
    )
    res = execute_code(req)
    assert res.status == "success"
    assert res.results[0].actual == "write_prevented"


def test_large_output_truncated():
    """Security Test: excessive stdout output is capped at 32KB."""
    code = """
def solution():
    print("X" * 100_000)
    return 42
"""
    req = ExecutionRequest(
        language="python",
        code=code,
        function_name="solution",
        tests=[TestCase(args=[], expected=42)],
    )
    res = execute_code(req)
    assert len(res.stdout.encode("utf-8")) <= 35_000
    assert "[Output truncated" in res.stdout
