# AI-SDLC Compass

AI-SDLC Compass is an automated evaluation and advisory tool for software engineering teams. It analyzes repository architecture and team context across four SDLC domains:

1. **Requirements & design** (`requirements_design`)
2. **Development** (`code_refactoring`)
3. **Testing** (`qa_testing`)
4. **Deployment & monitoring** (`devops_monitoring`)

---

## Directory Structure

```text
SDLC-Compass/
├── backend/            # FastAPI backend and multi-agent diagnostic engine
├── frontend/           # Vue 3 + Vite + TypeScript application
├── frontend-legacy/    # Original vanilla prototype UI (preserved)
├── docs/               # Architecture guides and API contracts
└── tests/              # Backend pytest test suite
```

---

## 1. Running the Backend

### Prerequisites

- Python 3.10 or later (tested on Python 3.12)
- pip

### Install backend dependencies

Run from the `SDLC-Compass/` directory (not the repo root):

```powershell
cd SDLC-Compass
pip install -r backend/requirements.txt
```

> **Note**: `pytest` and `httpx` are used by the test suite but are not listed in
> `backend/requirements.txt`. Install them separately if needed:
>
> ```powershell
> pip install pytest httpx
> ```

### Start the FastAPI server

```powershell
# Still from SDLC-Compass/:
uvicorn backend.main:app --port 8000 --reload
```

The API is available at **`http://localhost:8000`**.
Interactive docs (Swagger UI) are at **`http://localhost:8000/docs`**.

On first start the backend automatically creates:

- `SDLC-Compass/backend/data/` — SQLite database and workspace files
- `SDLC-Compass/backend/data/workspaces/` — cloned / extracted repositories
- `SDLC-Compass/backend/data/reports/` — generated HTML / PDF reports

No manual database setup is required.

### LLM provider

The backend defaults to **Ollama** (`http://localhost:11434`, model `llama3.1`).
Report synthesis will fail if Ollama is not running or the model is not pulled.

```powershell
# Pull the default model once (requires Ollama installed):
ollama pull llama3.1
```

To switch provider, set environment variables before starting uvicorn (or add them
to a `.env` file in `SDLC-Compass/`):

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
```

---

## 2. Running Backend Tests

```powershell
# From SDLC-Compass/:
pytest tests/test_api.py -v
```

All four tests use an in-process `TestClient` — no running server needed.

---

## 3. Running the Frontend (Vue 3 + Vite)

### Prerequisites

- Node.js 18 or later
- npm (comes with Node.js)

### Install frontend dependencies

```powershell
cd SDLC-Compass/frontend
npm install
```

`package-lock.json` is committed; `npm install` reproduces the exact dependency tree.

### Start the development server

```powershell
npm run dev
```

The frontend is available at **`http://localhost:5173`**.

---

## 4. Environment Variables

All frontend environment variables are stored in `SDLC-Compass/frontend/.env`.
The file is **gitignored**; copy from `.env.example` if starting fresh:

```powershell
cp SDLC-Compass/frontend/.env.example SDLC-Compass/frontend/.env
```

| Variable | Default | Description |
|---|---|---|
| `VITE_USE_MOCKS` | `true` | `true` = offline mock mode; `false` = real backend |
| `VITE_API_BASE` | `http://localhost:8000/api/v1` | Backend API base URL |
| `VITE_REPORT_TIMEOUT_MS` | `180000` | Synthesis timeout in ms (default 3 min) |

---

## 5. Switching Between Mocks and Real Backend

### Mode A — Standalone Mock Mode (Default)

Out of the box the frontend uses in-memory fixture data and never contacts the backend:

```env
# SDLC-Compass/frontend/.env
VITE_USE_MOCKS=true
VITE_API_BASE=http://localhost:8000/api/v1
```

Start only the frontend:

```powershell
cd SDLC-Compass/frontend
npm run dev
```

### Mode B — Connected Real Backend Mode

1. **Start the backend** (in one terminal):

   ```powershell
   cd SDLC-Compass
   uvicorn backend.main:app --port 8000
   ```

2. **Update the frontend `.env`**:

   ```env
   VITE_USE_MOCKS=false
   VITE_API_BASE=http://localhost:8000/api/v1
   ```

3. **Start the frontend** (in a second terminal):

   ```powershell
   cd SDLC-Compass/frontend
   npm run dev
   ```

The frontend calls the backend directly at `http://localhost:8000` — CORS is open
for all origins in development. There is **no Vite proxy** configured; the full
`VITE_API_BASE` URL is used for every request.

---

## 6. PDF Report Export & WeasyPrint

The backend generates reports via `GET /sessions/{id}/report/pdf`.

| Platform | Behaviour |
|---|---|
| Linux / macOS | PDF rendered via WeasyPrint if GTK3/Cairo libraries are available |
| Windows (no GTK3) | Falls back gracefully to a styled standalone `.html` deliverable |

**Missing system libraries on Windows**: WeasyPrint requires native C runtime DLLs
(`libgobject-2.0-0.dll`, `libpango-1.0-0.dll`, `libcairo-2.dll`). Without them,
WeasyPrint logs `OSError: cannot load library 'libgobject-2.0-0': error 0x7e` and
the backend serves `.html` instead — no crash, no user action needed.

To enable native PDF rendering on Windows, install GTK3 via MSYS2:

```bash
pacman -S mingw-w64-x86_64-gtk3 mingw-w64-x86_64-pango
```

Or follow the
[WeasyPrint Windows installation guide](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows).
