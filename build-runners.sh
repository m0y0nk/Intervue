#!/usr/bin/env bash
# Build the sandboxed runner images that the executor spawns at runtime.
# Run this ONCE before `docker compose up`, and again whenever a harness file changes.
set -e

EXEC_DIR="$(cd "$(dirname "$0")/backend/app/execution" && pwd)"

echo "==> Building intervue-runner-python:latest"
docker build -f "$EXEC_DIR/Dockerfile.python" -t intervue-runner-python:latest "$EXEC_DIR"

echo "==> Building intervue-runner-java:latest"
docker build -f "$EXEC_DIR/Dockerfile.java" -t intervue-runner-java:latest "$EXEC_DIR"

echo "==> Building intervue-runner-cpp:latest"
docker build -f "$EXEC_DIR/Dockerfile.cpp" -t intervue-runner-cpp:latest "$EXEC_DIR"

echo ""
echo "All runner images built. You can now run: docker compose up --build"
