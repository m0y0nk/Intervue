# SPEC: AI Technical Interview Simulator (v2)

Locally runnable simulator of a 20-minute coding interview. The AI acts as an **interviewer who evaluates**, never a tutor who helps. Single user, no auth, runs on localhost via Docker Compose.

---

## 0. How you (the coding agent) must work

1. **Do not write code yet.** First reply with: architecture summary, technical risks, the plan for the thin slice (section 14), and a numbered list of **assumptions and open questions**. Then **stop and wait for my approval**.
2. After approval, implement **one phase at a time** (section 14). At the end of each phase: run the phase's tests, report what passes, and stop for my go-ahead.
3. If this spec conflicts with itself or is ambiguous, ask. Do not silently pick.
4. Keep the app runnable at the end of every phase.
5. Build **one unified interview engine**. Question source, practice mode and interview style are independent config inputs. Never write per-mode or per-source interview engines.

Priorities, in order: interview correctness, problem quality, evaluation reliability, execution security, timer reliability, UX.

---

## 1. Stack and versions

| Area | Choice |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui, lucide-react |
| Code editor | CodeMirror 6 with **all** autocomplete, hints, linting and snippets disabled (or Monaco with every suggestion feature off). Plain text feel. |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic (optional) |
| LLM | Official `google-genai` SDK. Model from env `GEMINI_MODEL` (default `gemini-2.5-flash`; confirm current name in the Gemini docs and flag it to me). |
| DB | SQLite file on a Docker volume |
| Infra | Docker, Docker Compose, `.env`, `.env.example` |

`.env.example` must contain: `GEMINI_API_KEY=your_api_key`, `GEMINI_MODEL=`, `GEMINI_TIMEOUT_SECONDS=60`, `DATABASE_URL=`, and executor settings. I create the real `.env`.

Ask me which host OS I use (Windows/Mac/Linux) before finalizing Docker setup.

---

## 2. Configuration model (three independent dimensions)

```text
InterviewConfig {
  source:     ai_business | leetcode | random_dsa | adaptive | custom
  mode:       standard | blind_mock | topic_mastery | revision
  style:      google | amazon | meta | general
  difficulty: easy | medium | hard | adaptive
  category:   arrays_hashing | two_pointers | sliding_window | binary_search |
              stack_queue | linked_lists | trees | graphs | dynamic_programming |
              greedy | backtracking | heaps | intervals | mixed
  language:   java (default) | python | cpp
  framing:    standard | business          (random_dsa only)
  duration:   fixed 20 minutes, not configurable
}
```

Modes are **filters/behaviors applied on top of a source**, not generators:
- `standard`: metadata may be shown on the setup screen.
- `blind_mock`: **server-side** redaction. API responses for the session must omit title, ID, difficulty, category, expected complexity and hints. The UI must never receive them (enforced by a `ProblemPublicBlind` response schema). Interviewer prompts also exclude them.
- `topic_mastery`: requires `category != mixed`. Constrains problem selection only. Tracks per-category performance. Difficulty may step up after consecutive strong results.
- `revision`: requires existing history. Loads a past problem (same statement), hides prior solution/feedback until the new attempt is finished, then shows a comparison against the previous attempt.

Compatibility validation (return 422 with a clear message):
- `topic_mastery` with `category = mixed`: invalid.
- `revision` with no prior attempts: invalid.
- `revision` with `source` not matching a prior problem: invalid.
- `adaptive` source with fewer than **5 completed interviews and fewer than 2 in any category**: reject and tell the user to use Random Practice or pick a topic. Never fabricate history.
- `blind_mock` combined with any source or mode: allowed (redaction rules above).
- `topic_mastery` + `blind_mock`: allowed; category chosen but never shown during the interview.

Interview style is a **parameter table** (put in `config/styles.py`, unit-tested):

| Param | google | amazon | meta | general |
|---|---|---|---|---|
| max_follow_ups_per_stage | 3 | 2 | 2 | 2 |
| tone | probing, terse | structured, ownership-minded | fast, product-minded | neutral |
| rubric weights | higher on optimal approach and complexity | higher on edge cases and code quality | higher on coding speed and correctness | balanced |
| report wording | neutral | neutral | neutral | neutral |

Do not claim to reproduce any company's proprietary rubric or actual questions.

---

## 3. Problem model

Two Pydantic models in separate modules so private data cannot reach the wrong route:

- `ProblemPublic`: id, statement, examples (visible), signature, revealed constraints (per stage), visible tests. Blind variant omits metadata.
- `ProblemPrivate`: everything in public, plus categories, difficulty, brute-force and optimal approach descriptions, alternative valid approaches, time/space complexity, **one Python reference solution**, independent brute-force solution, hidden tests (inputs and expected outputs), edge-case definitions, evaluation rubric.

Only `evaluation_service` and `problem_validator` may import `ProblemPrivate`. Interviewer routes, interviewer service and all frontend-facing schemas import `ProblemPublic` only. Add a test that fails if `interviewer_service` imports `ProblemPrivate`.

### 3.1 Language-neutral I/O contract

Each problem declares a function signature using a closed type set:

`int, long, double, bool, string, int[], int[][], string[], ListNode, TreeNode`, graphs as `int n + int[][] edges`.

- Tests are stored as JSON: `{ "args": [...], "expected": ... }`.
- Linked lists serialize as arrays; trees as level-order arrays with `null`.
- Each problem has a `checker`: `exact | unordered | float_tolerance(eps)`.
- Per-language **harness templates** (Java, Python, C++) parse JSON args, call the candidate's function, serialize output, and print JSON. Candidates write only the function body in the starter template.
- Reference solutions exist **only in Python**. Expected outputs for hidden tests are produced by running that reference in the sandbox at generation time.

### 3.2 Validation pipeline (must pass before any problem is shown)

LLM self-checking is not sufficient. Use differential testing in the sandbox:

1. Schema validation (Pydantic).
2. Run Python reference on all visible examples. Output must equal the stated expected output.
3. Gemini also produces an **independent brute-force** solution. Generate N random inputs (Gemini supplies a small input-generator function respecting constraints, run in the sandbox). Reference and brute force must agree on all N (default N=200, small sizes). Disagreement: reject and regenerate.
4. Run reference on max-size inputs; it must finish within the time limit. Check that a naive O(n²)/exponential approach would exceed it when the intended optimal complexity differs (best effort).
5. Compute hidden test expected outputs via the reference.
6. Best-effort checks, clearly labeled as LLM-judged: solvable in 20 minutes, statement doesn't name the algorithm or data structure.
7. Max 3 regeneration attempts, then fail with a user-visible error.

Do **not** translate reference solutions to Java/C++. Instead, verify in CI that each language's harness works against a small known-good fixture solution for each supported type.

Problem generation is **async**: `POST /sessions` returns `generating`, the frontend polls and shows a progress screen. **The timer starts only after the problem is validated and displayed to the candidate** (candidate clicks Begin).

---

## 4. Question sources

1. **ai_business**: Gemini invents a business scenario (e-commerce, logistics, finance, social networks, cloud infra, streaming, healthcare tech, supply chain) that hides an underlying DSA problem. At least 3 examples, ambiguity that is solvable, no algorithm disclosure. Passes section 3.2.
2. **leetcode**: LeetCode has **no official public API**, and its GraphQL endpoint is undocumented. Do not scrape or depend on it. Primary path: the user enters an ID **and pastes the original statement** (with examples and constraints). Optionally ask me about a licensed dataset to support lookup by ID, and flag the licensing question instead of guessing. Gemini is **not** trusted to recall a statement by ID. Preserve the pasted requirements, convert to the signature format, then run section 3.2. Never reveal title, difficulty, category or editorial hints.
3. **random_dsa**: Gemini picks an underlying problem matching difficulty/category/framing. Avoid recently attempted problems (compare against stored problem fingerprints: normalized title/signature hash plus category). Keep generation history.
4. **adaptive**: deterministic Python/SQL computes weaknesses from stored scores (lowest dimension averages, per-category averages, repeated gap types). Selection rules map weaknesses to category/difficulty/problem traits. Gemini may only phrase the recommendation, never invent scores. Avoid repeats and raise difficulty gradually.
5. **custom**: user pastes statement, optional URL, optional extra constraints. Convert, generate reference and hidden tests, run section 3.2. If a reliable reference cannot be produced (validation fails after retries), mark the problem **unsupported** and do not start an interview.

All sources feed the same `ProblemPrivate` structure and the same interview engine.

---

## 5. Interview engine and stages

The backend owns all state. Gemini **never** controls the timer, stage transitions or termination.

| Stage | Name | Target window |
|---|---|---|
| 1 | Understanding | 0:00–3:00 |
| 2 | Brute force | 3:00–6:00 |
| 3 | Constraint analysis | 6:00–8:00 |
| 4 | Optimal approach | 8:00–11:00 |
| 5 | Edge cases | 11:00–13:00 |
| 6 | Coding | 13:00–20:00 |

Rules:
- The **candidate advances** stages with a Next button. Backend enforces order and forbids returning to earlier stages once coding starts.
- Windows are soft except two hard rules: at **13:00** the backend forces the move into Coding (notes saved as-is), and at **20:00** it terminates the session.
- Stage 3 reveals constraints (input size, value ranges, memory limits, sorting/duplicate assumptions). Revealing is a backend action triggered by entering stage 3, not by Gemini.
- Stage 2 brute-force coding is optional. Stage 4 accepts any valid approach.
- Record per-stage start/end timestamps (active time) for scoring Time Management.

### 5.1 Timer

Persist, per session: `status` (running/paused/finished/abandoned), `active_ms_accumulated`, `last_resumed_at` (server UTC wall clock), `started_at`.

`remaining = 1_200_000 - (active_ms_accumulated + (now - last_resumed_at if running))`.

Pause adds elapsed time to `active_ms_accumulated`. The frontend only **renders** a countdown computed from the server's `remaining_ms` and re-syncs on refresh, tab focus and every 15 s. It never owns the truth. Survives server restarts (wall clock + persisted fields). Warnings at 5:00 and 2:00 remaining. Auto-termination is a backend check on every request plus a background task.

**Reset** abandons the current attempt (marked `abandoned`, kept in history, excluded from score stats) and creates a fresh session. Unlimited pause is allowed but paused time is not counted.

---

## 6. Gemini architecture and isolation

Two logical agents with separate prompt builders, separate Pydantic response schemas and separate service modules.

**Interviewer agent** (`interviewer_service`): sees only `ProblemPublic`, the current stage, the candidate's notes and chat, the style parameters, and a narrow **signal** from the evaluator. It asks clarifying and follow-up questions, challenges assumptions, asks complexity questions, and gives brief acknowledgements. It must never give hints or solutions. Output schema has a short `message` and nothing else.

**Evaluator agent** (`evaluation_service`): may read `ProblemPrivate`. During the interview it emits **only a schema-limited signal** to the backend:

```json
{ "on_track": true, "gap_type": "none|misread_problem|missing_bruteforce|wrong_complexity|missed_constraint|wrong_approach|missing_edge_case|unclear_communication",
  "probe_type": "clarify|complexity|correctness|edge_case|none" }
```

No free text derived from the rubric or reference. The backend passes this signal to the interviewer, which writes the actual question without access to private data. Full evaluation happens only after the interview ends.

Enforcement must be structural: separate modules, typed signatures, import-boundary test, and a test that the interviewer's prompt string never contains any substring of reference code, hidden tests or rubric for a seeded problem.

**The Coding stage triggers zero LLM calls** (assert in tests). No autocomplete, hints, debugging help or algorithm suggestions anywhere in solving mode.

### 6.1 Robustness

All Gemini calls: structured JSON output, Pydantic validation, timeout, bounded retries with backoff, handling for rate limits (429), malformed JSON (one repair retry, then fail cleanly), and API key errors. Surface clear user-facing errors. Key stays in the backend only; never sent to the frontend or logged.

Evaluation settings: low temperature, anchored scales, evidence quotes per score.

---

## 7. Code execution (security-critical)

FastAPI must **never** execute candidate code.

Design:
- A separate **`executor` service** in Compose. The backend calls it over an internal network API. Only the executor has access to the Docker socket. Document plainly that docker-socket access is privileged and acceptable only for local single-user use; mention rootless Docker or gVisor as hardening options.
- Pre-built, pinned runner images for Java, Python, C++ (`backend/app/execution/Dockerfile.*`). **No image builds per run.**
- Each run starts a fresh container with: `--network none`, `--read-only`, tmpfs workdir with size limit, `--cap-drop ALL`, `--security-opt no-new-privileges`, non-root user, `--pids-limit`, memory limit (default 256 MB), CPU limit (1), wall-clock timeout (default 5 s per test, 15 s per run), output size cap. Container is removed after each run.
- Capture and return: compile errors, runtime errors, timeouts, memory-limit kills, stdout/stderr (truncated).
- The harness (section 3.1) runs tests; test data is mounted read-only and never returned.

Run vs Submit:
- **Run Code** executes **visible tests only** and shows inputs, expected and actual for those tests.
- **Submit / end of interview** executes hidden tests **once**. Report counts only (passed/total plus category of failure like wrong answer, TLE, runtime error). **Never expose hidden inputs or expected outputs**, to avoid binary-search leakage through repeated Run calls.
- Rate-limit Run Code (for example 1 per 5 s).

Security tests required: network blocked, fork bomb contained, memory bomb killed, infinite loop times out, filesystem writes outside tmpfs fail, large output truncated.

---

## 8. Evaluation and report

Ten dimensions scored 0–10: Problem Understanding, Communication, Brute Force Reasoning, Constraint Analysis, Optimal Approach, Complexity Analysis, Edge Cases, Coding Ability, Code Quality, Time Management.

- **Deterministic**: Coding Ability (from hidden test pass rate and failure categories) and Time Management (from stage timings vs windows) are computed in Python, not by the LLM.
- **LLM-scored** (anchored rubric scales, evidence quotes required): the remaining eight. Candidate notes and chat are the evidence.
- Accept alternative valid approaches; compare against rubric criteria, not only the reference.
- Output: total score (weighted by style), verdict `strong_hire | hire | borderline | no_hire` using **fixed numeric thresholds in config** (not LLM judgment), strengths, weaknesses, coding evaluation, tests passed, runtime/memory stats, and specific improvement recommendations.
- **Idea-to-Code Gap**: present algorithmic-reasoning score next to implementation score, plus an LLM-written explanation of *why* the implementation diverged (for example off-by-one, wrong data structure use, missed edge case, syntax trouble) grounded in test failures. Do not present raw subtraction as a statistical metric; trend charts show both series.

---

## 9. Persistence and dashboard

Tables (suggested): `sessions`, `problems` (public + private JSON, fingerprint), `stage_events`, `notes`, `chat_messages`, `code_snapshots`, `run_results`, `evaluations`, `dimension_scores`, `weakness_tags`.

Persist everything listed in the product requirements: date, source, problem id, mode, style, difficulty, category, language, stage timings, scores, test results, feedback, weaknesses. Autosave notes and code every few seconds. Session recovery after refresh/crash/restart returns the user to the same stage with correct remaining time.

Dashboard metrics (deterministic SQL/Python only): total interviews, average score, coding accuracy, average implementation score, Idea-to-Code trend, strongest/weakest dimensions, performance by category, recent attempts. Gemini may write an interpretation and recommendations from these computed numbers; it never computes them.

---

## 10. Frontend

Pages: `Dashboard`, `InterviewSetup`, `InterviewWorkspace`, `Results`.

- **Setup**: five source cards; fields appear only for the selected source; mode, style, difficulty, category, language (Java default), fixed duration label. Show validation errors inline. Revision shows filters (failed, partial, passed, weakest categories, most recent).
- **Workspace**: left problem panel (statement, examples, revealed constraints); center notes sections for the six stages that feel like natural notes plus the plain code editor in stage 6; right interviewer panel (questions, replies, brief acknowledgements; no open-ended chatbot); header with remaining time, language, stage, pause/resume, reset, end interview.
- Responsive, keyboard accessible, minimal distraction, autosave indicators, session recovery.
- Editor: no autocomplete, no snippets, no bracket-completion AI, no hints. Minimal language starter templates only.

---

## 11. Backend layout

```text
backend/app/
  main.py  config.py
  api/        sessions.py interview.py problems.py execution.py evaluation.py dashboard.py
  services/   gemini_service.py problem_generator.py problem_retriever.py problem_validator.py
              interviewer_service.py evaluation_service.py timer_service.py
              code_execution_service.py adaptive_practice_service.py stats_service.py
  models/  schemas/  database/  config/styles.py
  prompts/    problem_generation.py interviewer.py stage_evaluation.py final_evaluation.py
  execution/  Dockerfile.python Dockerfile.java Dockerfile.cpp harness/
executor/     (separate service)
frontend/src/ components/{Timer,ProblemPanel,InterviewerPanel,NotesEditor,CodeEditor,Evaluation} pages hooks services types
docker-compose.yml  .env.example  README.md
```

Keep LLM code separate from deterministic interview mechanics.

---

## 12. API sketch (finalize in your plan)

`POST /api/sessions` (config in, 202 + session id) · `GET /api/sessions/{id}` (state, remaining_ms, public problem) · `POST /sessions/{id}/begin` · `/pause` · `/resume` · `/reset` · `/end` · `POST /sessions/{id}/stage/next` · `PUT /sessions/{id}/notes` · `PUT /sessions/{id}/code` · `POST /sessions/{id}/interviewer` (pre-coding only; 409 in stage 6) · `POST /sessions/{id}/run` (visible tests) · `POST /sessions/{id}/submit` (hidden tests once) · `GET /sessions/{id}/report` · `GET /history`, `/dashboard`, `/revision/candidates`.

---

## 13. Testing requirements

Unit: config compatibility matrix, style params, timer math (pause/resume/restart), stage state machine, stats SQL, blind-mode redaction, adaptive cold-start rejection, verdict thresholds.
Integration: validation pipeline with a mocked Gemini returning good and bad problems (bad ones must be rejected), full session flow with mocked Gemini, session recovery after restart.
Isolation: import-boundary test, prompt-leak test, no Gemini calls in coding stage, hidden tests never in any API response.
Security: the executor tests in section 7.
Gemini failure handling: timeout, 429, malformed JSON, key missing.

Use a mock Gemini client by default in CI so tests need no API key.

---

## 14. Phases (each ends with tests + my approval)

**Phase 0 (plan only):** the response described in section 0. No code.

**Phase 1: Thin vertical slice.** Random DSA + Standard mode + General style + **Python only** + executor service with Docker isolation + validation pipeline (reference + brute-force differential) + backend timer + six-stage flow + minimal editor + hidden-test submit + basic report. Docker Compose runs everything.
*Done when:* I can run `docker compose up`, start a random Python interview, pass through all stages, run visible tests, submit, and see a report; timer survives refresh and restart; security tests pass.

**Phase 2:** Java and C++ harnesses and runner images. *Done when* each language passes fixture tests per type and the section 7 security tests.

**Phase 3:** Configuration engine: all modes, all styles, compatibility validation, blind-mode redaction. *Done when* the section 13 config tests pass.

**Phase 4:** Remaining sources: ai_business, custom (with unsupported handling), leetcode (paste path), adaptive (history-based with cold-start rejection).

**Phase 5:** Full evaluation: evaluator signal to interviewer, anchored scoring, deterministic coding/time scores, Idea-to-Code Gap, revision comparison.

**Phase 6:** Dashboard, analytics, Gemini-written recommendations from computed stats, category tracking.

**Phase 7:** Hardening: end-to-end tests, Gemini failure handling, README with setup, security review, known limitations.

---

## 15. Acceptance criteria

1. `docker compose up` runs the full app locally.
2. All five sources and four modes work and compose where compatible; incompatible combinations are rejected with clear errors.
3. No problem is shown unless it passes the validation pipeline; unsupported problems are refused.
4. Blind Mock hides title, ID, difficulty, category and complexity at the API level.
5. Business scenarios do not name the algorithm.
6. Adaptive practice uses only real history and refuses on cold start.
7. Revision gives a true fresh attempt and a comparison afterwards.
8. Interviewer never receives private data; no hints or solutions leak; zero Gemini calls during coding.
9. Timer is backend-authoritative, pause-aware, restart-safe, and hard-stops at 20 active minutes.
10. Editor has no AI assistance of any kind.
11. Java, Python and C++ run in isolated containers with the limits in section 7.
12. Hidden test data and reference solutions are never exposed through any endpoint.
13. Final report includes scores, verdict, tests, and Idea-to-Code Gap.
14. History persists across restarts; automated tests cover the critical paths.

---

**Reminder:** you are building an interview simulator, not a chatbot with an editor. Plan first, then stop for approval.
