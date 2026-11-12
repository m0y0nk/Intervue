# Intervue — AI Technical Interview Simulator

A locally runnable simulator of a rigorous 20-minute technical coding interview. The AI acts as an **evaluator who assesses**, never a tutor who helps. All interview logic is deterministic and backend-authoritative.

---

## Architecture

```
                      +---------------------------------------+
                      |       Frontend (Vite / React 18)      |
                      |  - CodeMirror 6 (autocomplete OFF)    |
                      |  - Authoritative Synchronized Timer   |
                      |  - 3-Panel Workspace                  |
                      |  - Dashboard & Analytics              |
                      +-------------------+-------------------+
                                          | REST / JSON
                                          v
                      +---------------------------------------+
                      |       Backend API (FastAPI)           |
                      |  - Unified Interview Engine           |
                      |  - Wall-clock Restart-Safe Timer      |
                      |  - Session & Problem SQLite Store     |
                      |  - Dashboard Stats Service (SQL)      |
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

## Features

- **5 Problem Sources**: Random DSA, AI Business Scenario, LeetCode Paste, Custom Statement, Adaptive (history-based)
- **4 Interview Modes**: Standard, Blind Mock, Topic Mastery, Revision (with before/after comparison)
- **4 Company Styles**: Google, Amazon, Meta, General
- **3 Languages**: Python, Java, C++ — all in isolated Docker containers
- **Full 6-Stage Flow**: Problem Understanding → Brute Force → Constraints → Optimal Approach → Edge Cases → Coding
- **Anchored Scoring**: 8 LLM dimensions + 2 deterministic (coding accuracy, time management)
- **Idea-to-Code Gap**: Tracks divergence between algorithmic reasoning and implementation quality
- **Dashboard**: Deterministic SQL analytics, verdict history, category performance, Gemini coaching recommendations
- **Revision Mode**: Re-attempt a past problem; get a side-by-side improvement comparison

---

## Quickstart

### Prerequisites
- Docker Desktop running
- Python 3.12+
- Node.js 20+

### 1. Clone & Configure
```bash
git clone https://github.com/m0y0nk/Intervue.git
cd Intervue
cp .env.example .env
# Edit .env — add your GEMINI_API_KEY (optional; app works without it in mock mode)
```

### 2. Run via Docker Compose
```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API Docs | http://localhost:8000/docs |
| Executor Health | http://localhost:8001/health |

> **Without a Gemini API key**, the app runs in deterministic sandbox mode: all LLM calls fall back to a validated mock (Pair Sum Target problem). Evaluation, timer, execution, and history all work normally.

---

## Local Development

### Backend
```bash
cd backend
python -m venv ../venv
source ../venv/bin/activate   # Windows: ..\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev    # Vite dev server at http://localhost:5173
```

### Executor (required for code execution)
```bash
# Start Docker Desktop first, then:
docker compose up executor
```

---

## Automated Test Suite

```bash
source venv/bin/activate
pytest tests/ -v
```

**82 tests across 10 test modules:**

| Module | Tests | Covers |
|--------|-------|--------|
| `test_config_engine.py` | 12 | All 422 config validation rules, blind mock redaction |
| `test_dashboard.py` | 17 | Stats aggregation, pagination, revision candidates, Gemini recommendations |
| `test_evaluation_pipeline.py` | 6 | Anchored scoring, deterministic scores, revision comparison |
| `test_executor_security.py` | 8 | Network isolation, timeout, memory bomb, fork bomb, filesystem |
| `test_hardening.py` | 26 | End-to-end acceptance criteria, privacy isolation, Gemini failure handling |
| `test_isolation.py` | 3 | AST import boundary, zero LLM in coding stage, prompt leak guard |
| `test_language_fixtures.py` | 25 | Python/Java/C++ type marshaling, container security |
| `test_session_flow.py` | 1 | Full session lifecycle (create → begin → stages → submit → report) |
| `test_sources.py` | 5 | All 5 problem sources, adaptive cold-start rejection |
| `test_styles_config.py` | 1 | Style parameter validation |
| `test_timer.py` | 4 | Timer precision, pause/resume, auto-advance, auto-terminate |

> Docker must be running for `test_executor_security.py` and `test_language_fixtures.py`.

---

## Security & Sandboxing

### Code Execution Isolation
Every candidate code submission runs inside an ephemeral Docker container with:
- `--network none` — Outbound network completely blocked
- `--read-only` — Root filesystem read-only
- `tmpfs` — Write space limited to size-capped tmpfs only
- `--cap-drop ALL` + `--security-opt no-new-privileges` — All kernel capabilities dropped
- Non-root user (`sandbox`, UID 1000)
- Memory hard-cap: 256MB, swap disabled
- CPU cap: 1.0 core
- Process limit: `--pids-limit 64`
- Per-test timeout: 5s; total execution timeout: 15s

### Private Data Isolation
- `ProblemPrivate` (contains `hidden_tests`, `python_reference`, `python_brute_force`, `rubric`) is **only** accessible to `evaluation_service` and `problem_validator`.
- `interviewer_service` is AST-audited (see `test_isolation.py`) to confirm it never imports `ProblemPrivate`.
- The `GET /sessions/{id}` endpoint only serializes `ProblemPublic` or `ProblemPublicBlind` — never private fields.
- The evaluation `report_json` stored in DB is typed as `FinalEvaluationReport` which contains no private problem fields.
- Zero LLM calls occur during Stage 6 (Coding). The `/interviewer` endpoint returns 409 if called in Stage 6.

### Blind Mock Redaction
When `mode = blind_mock`, the backend server-side redacts:
- `problem.id`, `problem.title`, `problem.difficulty`, `problem.category`
- `config.difficulty`, `config.category`

These fields are `None` in the API response — they never reach the frontend.

---

## Configuration Reference

### Environment Variables (`.env`)
```env
GEMINI_API_KEY=          # Optional. Leave blank for mock mode.
GEMINI_MODEL=gemini-2.0-flash-exp   # Gemini model to use
DATABASE_URL=sqlite:///./intervue.db  # Path to SQLite DB
EXECUTOR_URL=http://localhost:8001    # Executor service URL
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### Interview Configuration
| Field | Values | Notes |
|-------|--------|-------|
| `source` | `random_dsa`, `ai_business`, `adaptive`, `leetcode`, `custom` | |
| `mode` | `standard`, `blind_mock`, `topic_mastery`, `revision` | |
| `style` | `google`, `amazon`, `meta`, `general` | Affects scoring weights |
| `difficulty` | `easy`, `medium`, `hard`, `adaptive` | `adaptive` only with `source=adaptive` |
| `category` | 13 DSA categories + `mixed` | `mixed` blocked in `topic_mastery` |
| `language` | `python`, `java`, `cpp` | |
| `duration` | `1200` | Fixed at 20 minutes |

### Scoring & Verdict Thresholds
| Verdict | Threshold |
|---------|-----------|
| `strong_hire` | ≥ 8.5 / 10 |
| `hire` | ≥ 7.0 / 10 |
| `borderline` | ≥ 5.5 / 10 |
| `no_hire` | < 5.5 / 10 |

Thresholds are config constants — never LLM judgment.

---

## API Reference

```
POST   /api/sessions                     Create session (202 Accepted, async generation)
GET    /api/sessions/{id}                Get session state + timer
POST   /api/sessions/{id}/begin          Start timer
POST   /api/sessions/{id}/pause          Pause timer
POST   /api/sessions/{id}/resume         Resume timer
POST   /api/sessions/{id}/reset          Abandon and reset
POST   /api/sessions/{id}/stage/next     Advance to next stage
PUT    /api/sessions/{id}/notes          Save notes for a stage
PUT    /api/sessions/{id}/code           Save current code (debounced by frontend)
POST   /api/sessions/{id}/interviewer    Chat with AI interviewer (stages 1-5 only)
POST   /api/sessions/{id}/run            Run against visible tests (rate-limited: 1/5s)
POST   /api/sessions/{id}/submit         Run hidden tests & generate evaluation
GET    /api/sessions/{id}/report         Get final evaluation report
GET    /api/dashboard                    Deterministic analytics stats
GET    /api/dashboard/recommendations    Gemini coaching narrative (from stats only)
GET    /api/history                      Paginated session history
GET    /api/revision/candidates          Sessions eligible for revision mode
GET    /health                           Backend health check
```

---

## Known Limitations

1. **SQLite single-writer**: Only suitable for single-user local use. For multi-user deployment, swap `DATABASE_URL` to PostgreSQL — SQLAlchemy ORM is compatible.

2. **Gemini `additionalProperties` constraint**: The structured output API (`response_schema`) is not supported in Gemini Developer API mode (only in Enterprise Agent Platform). The app falls back to the mock response automatically. Free-text generation via `generate_free_text` works without this restriction.

3. **Docker socket access required**: The executor service requires Docker socket access to spawn ephemeral containers. In restricted environments (e.g., CI without Docker), `test_executor_security.py` and `test_language_fixtures.py` will fail — this is expected.

4. **LeetCode paste source**: Only parses the problem statement pasted as text — no scraping. The user must manually copy the full statement, examples, and constraints into the input field.

5. **Custom source validation**: Custom problem statements must include at least one example and a function signature identifiable by Gemini. Ambiguous or incomplete statements will be refused.

6. **Adaptive requires 5+ interviews, 2+ per category**: Cold-start is enforced server-side and returns a 422 explaining the requirement.

7. **Code editor has no AI assistance by design**: This is intentional. The `/interviewer` endpoint returns 409 during Stage 6 (Coding). No autocomplete, Copilot, or suggestion tools are connected.

8. **Timer is wall-clock based, not CPU-based**: Pausing the browser tab pauses the interview (pause must be explicit). Background time while paused is not counted.

9. **No multi-language switching mid-session**: Language is set at session creation and cannot be changed. Reset and start a new session to switch.

10. **Report uses last 12 chat messages**: The LLM evaluation prompt includes only the last 12 messages from the chat log to stay within context limits. Longer conversations may have earlier messages excluded from evaluation.

---

## Development Build

```bash
# Full production build (TypeScript strict check + Vite bundle)
cd frontend && npm run build

# Backend type checking
cd backend && python -m mypy app/ --ignore-missing-imports
```

---

## Phases Completed

| Phase | Description | Commit |
|-------|-------------|--------|
| 1 | Thin vertical slice — Python executor, 6-stage flow, timer, report | `origin/main` |
| 2 | Java + C++ harnesses and runner images | `origin/main` |
| 3 | Config engine — all modes, blind-mode redaction, compatibility validation | `origin/main` |
| 4 | All 5 question sources — ai_business, adaptive, leetcode paste, custom | `origin/main` |
| 5 | Full evaluation pipeline — anchored scoring, Idea-to-Code Gap, revision comparison | `origin/main` |
| 6 | Dashboard, analytics, stats SQL, Gemini recommendations, category tracking | `origin/main` |
| 7 | Hardening — end-to-end acceptance tests, Gemini failure handling, security review | `origin/main` |
