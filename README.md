# Intervue - AI Technical Interview Simulator (v2)

Locally runnable simulator of a 20-minute technical coding interview. The AI acts as an **evaluator who assesses**, never a tutor who helps.

---

## Architecture Overview

```
                      +---------------------------------------+
                      |       Frontend (Vite / React 18)      |
                      |  - CodeMirror 6 (autocomplete OFF)    |
                      |  - Authoritative Synchronized Timer   |
                      |  - 3-Panel Workspace                  |
                      +-------------------+-------------------+
                                          | REST / JSON
                                          v
                      +---------------------------------------+
                      |       Backend API (FastAPI)           |
                      |  - Unified Interview Engine           |
                      |  - Wall-clock Restart-Safe Timer      |
                      |  - Session & Problem SQLite Store     |
                      +----------+-----------------+----------+
                                 |                 |
                   Internal HTTP |                 | google-genai SDK
                                 v                 v
+----------------------------------+     +----------------------------------+
|    Executor Service (Internal)   |     | Gemini Isolation Boundary        |
| - Spawns ephemeral containers    |     | - Interviewer Agent (Public only)|
| - Docker socket integration      |     | - Evaluator Agent (Private data) |
| - Strict sandboxing (--net none, |     | - Differential Validation Engine |
|   --read-only, tmpfs, pids/mem)  |     |   (Reference + Brute-force diff) |
| - Pinned runner images           |     +----------------------------------+
+----------------------------------+
```

---

## Security & Sandboxing Constraints

Code execution is isolated inside ephemeral containers with strict OS-level cgroup and namespace limits:
- `--network none`: Outbound socket and network connections are completely blocked.
- `--read-only`: Root filesystem is mounted read-only.
- `tmpfs`: Writable temporary space is restricted to size-capped tmpfs.
- `--cap-drop ALL` and `--security-opt no-new-privileges`: All Linux kernel capabilities dropped.
- Non-root user: Containers run as unprivileged `sandbox` user (UID 1000).
- Resource caps: Memory hard-capped at 256MB (swap disabled), CPU capped at 1.0 core, process count capped at `--pids-limit 64`.
- Strict execution timeouts: Per-test timeout (5s) and max-run timeout (15s) with wall-clock container termination.

---

## Quickstart

### 1. Prerequisites
- Docker & Docker Compose running.
- Python 3.12+ (for local test development).
- Node.js 20+ (for local frontend development).

### 2. Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Fill in your `GEMINI_API_KEY`. (If left blank, Intervue operates in deterministic sandbox mode using built-in validated problems for development and testing).

### 3. Launch via Docker Compose
```bash
docker compose up --build
```
Once running:
- **Frontend Workspace**: [http://localhost:5173](http://localhost:5173)
- **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Executor Health**: [http://localhost:8001/health](http://localhost:8001/health)

---

## Running the Automated Test Suite

Intervue includes unit, integration, and container security test suites:

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
pytest tests/ -v
```

### Verified Test Categories:
1. **Executor Security Tests** (`tests/test_executor_security.py`):
   - Outbound network blocked.
   - Infinite loop timeouts contained.
   - Memory bomb killed by 256MB limit.
   - Fork bomb contained by PIDs limit.
   - Filesystem writes outside tmpfs fail.
   - Excessive output truncated to 32KB.
2. **Structural Isolation Tests** (`tests/test_isolation.py`):
   - `interviewer_service` AST import boundary test (never imports `ProblemPrivate`).
   - Zero LLM calls in Coding stage (asserted and 409 returned).
   - Prompt leak tests (hidden tests and reference code never sent to interviewer).
3. **Timer & Persistence Tests** (`tests/test_timer.py`):
   - Wall-clock remaining time calculation.
   - Pause and resume persistence.
   - Auto-advance to Coding stage at 13:00.
   - Auto-terminate at 20:00.
4. **End-to-End Session Flow** (`tests/test_session_flow.py`):
   - Creation $\to$ Begin $\to$ Stage 1-6 progression $\to$ Run visible tests $\to$ Submit hidden tests $\to$ Evaluation Report generation.
