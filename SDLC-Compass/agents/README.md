# SDLC-Compass Agent Service

The Agent Service is an autonomous multi-agent diagnostic engine built with [FastAPI](https://fastapi.tiangolo.com/), [LangChain](https://www.langchain.com/), and [LangGraph](https://github.com/langchain-ai/langgraph), backed by local [Ollama](https://ollama.com/) LLMs (default: `qwen3:14b`).

It analyzes repositories across four SDLC domains, interacts with developers when repository inspection leaves questions unanswered, and synthesizes findings into an AI-SDLC readiness assessment.

---

## Architecture Overview

```
                                      ┌─────────────────────────────────────┐
                                      │       FastAPI Service (:8002)       │
                                      └──────────────────┬──────────────────┘
                                                         │
                                    ┌────────────────────▼────────────────────┐
                                    │      Diagnostic Pipeline Runner         │
                                    │        (agents/src/pipeline.py)         │
                                    └────────────────────┬────────────────────┘
                                                         │
             ┌─────────────────────────┬─────────────────┴───────┬─────────────────────────┐
             ▼                         ▼                         ▼                         ▼
   ┌───────────────────┐     ┌───────────────────┐     ┌───────────────────┐     ┌───────────────────┐
   │ 1. Requirements   │     │ 2. Code &         │     │ 3. QA &           │     │ 4. DevOps &       │
   │    & Design       │ ──> │    Refactoring    │ ──> │    Testing        │ ──> │    Monitoring     │
   │ (specifications)  │     │ (structure, types)│     │ (coverage, suites)│     │ (CI/CD, deploy)   │
   └─────────┬─────────┘     └─────────┬─────────┘     └─────────┬─────────┘     └─────────┬─────────┘
             │                         │                         │                         │
             └─────────────────────────┴─────────────┬───────────┴─────────────────────────┘
                                                     │
                                                     ▼
                                      ┌─────────────────────────────┐
                                      │      Final Synthesizer      │
                                      │ (Readiness Scorecard & Plan)│
                                      └─────────────────────────────┘
```

### Specialists
1. **Requirements & Design**: Evaluates specs, PRDs, ADRs, user stories, and requirements capture workflows.
2. **Code & Refactoring**: Inspects codebase modularity, static typing, dependency structure, and code quality.
3. **QA & Testing**: Analyzes test coverage, test frameworks, fixtures, and automated verification.
4. **DevOps & Monitoring**: Reviews CI/CD pipelines, containerization, observability, and deployment scripts.

### Human-in-the-Loop (`ask_user`)
Each specialist can pause its run using LangGraph's `interrupt()` via the `ask_user` tool if a key process detail cannot be determined directly from the codebase.
- When interrupted, the pipeline status becomes `needs_input`.
- The run state and memory are checkpointed to SQLite via `AsyncSqliteSaver`.
- Answering the question via `/pipeline/reply` resumes the specialist exactly where it left off.

---

## Prerequisites

1. **Python 3.12+**
2. **Ollama** running locally:
   ```bash
   ollama pull qwen3:14b
   ollama serve
   ```
   *Verify Ollama is reachable at `http://localhost:11434` (or `http://host.docker.internal:11434` from containers).*

---

## Local Setup

### 1. Create a Virtual Environment

**In Linux / WSL (recommended):**
```bash
cd SDLC-Compass/agents
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**In Windows (PowerShell):**
```powershell
cd SDLC-Compass\agents
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in `SDLC-Compass/agents/` (or copy from `.env.example` if available):

```ini
APP_NAME=SDLC-Compass-Agents
HOST=0.0.0.0
PORT=8002
DEBUG=true

# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
CHAT_MODEL=qwen3:14b
TEMPERATURE=0.0
```

---

## Running the Service

### Development Server (Uvicorn)
```bash
# From SDLC-Compass/agents:
.venv/bin/uvicorn src.main:app --port 8002 --reload
```
The server will initialize the SQLite checkpointer and start listening on `http://127.0.0.1:8002`.

### Docker Compose
Run the agents service as part of the full stack:
```bash
# From SDLC-Compass root:
docker compose up agents
```
*Note: Docker Compose automatically forwards host Ollama via `host.docker.internal` and mounts `./agents/data` for persistent checkpoints.*

### Interactive CLI Mode
To test the agent directly in your terminal without HTTP requests:
```bash
# From SDLC-Compass/agents:
.venv/bin/python -m src.main --cli
```

---

## API Endpoints

### 1. Health Check
```http
GET /health
```
**Response:**
```json
{
  "status": "healthy",
  "service": "SDLC-Compass-Agents",
  "model": "qwen3:14b",
  "ollama_host": "http://localhost:11434"
}
```

### 2. Ad-hoc Chat
```http
POST /chat
Content-Type: application/json

{
  "session_id": "session-1",
  "message": "What testing frameworks does this repository use?",
  "repo_path": "/path/to/repository"
}
```

### 3. Start Diagnostic Pipeline
Runs the 4 specialists sequentially followed by synthesis.

```http
POST /pipeline/start
Content-Type: application/json

{
  "session_id": "session-1",
  "repo_path": "/path/to/repository",
  "team_context": {},
  "background": false
}
```
- `background: false` (default): Holds connection until the turn pauses on a question (`needs_input`) or finishes (`complete`). Used by the backend supervisor.
- `background: true`: Returns `{"status": "accepted"}` immediately and runs in the background.

### 4. Resume Paused Pipeline
Resumes a specialist that paused on an `ask_user` clarifying question.

```http
POST /pipeline/reply
Content-Type: application/json

{
  "session_id": "session-1",
  "answer": "We write unit tests with pytest and run them on pull requests.",
  "background": false
}
```

### 5. Check Pipeline Status
Polls current execution status and active specialist progress.

```http
GET /pipeline/status?session_id=session-1
```
**Response during run:**
```json
{
  "session_id": "session-1",
  "status": "running",
  "current_index": 1,
  "total_specialists": 4,
  "current_role": "code_refactoring",
  "current_label": "Code & Refactoring",
  "completed_reports_count": 1,
  "result": null,
  "error": null
}
```

---

## Important Notes & Troubleshooting

### WSL Paths vs. Windows Paths
When running inside **WSL (Windows Subsystem for Linux)**, file paths passed as `repo_path` must use the Linux mount format, not Windows drive letters:
- **Correct (WSL):** `/mnt/c/Users/username/.../project`
- **Incorrect (Windows):** `C:\Users\username\...\project`

### Local Inference Latency
With `qwen3:14b` on consumer hardware, each specialist makes multiple LLM tool calls. A single specialist turn may take 2–5 minutes, and the full 4-agent pipeline can take 15–20 minutes.
- The backend's HTTP client timeout is configured via `AGENTS_REQUEST_TIMEOUT` (set to `1800` in `docker-compose.yml`).
- Monitor live server logs to see individual Ollama HTTP requests as each specialist reasons and inspects files.

### Data & Checkpoints
- Checkpoints and job state are stored in `agents/data/` (`checkpoints.db` and `pipeline_state.db`).
- This directory is gitignored and mounted as a volume in Docker Compose.
