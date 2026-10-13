# AI-SDLC Compass

AI-SDLC Compass is an automated evaluation and advisory tool for software engineering teams. It analyzes repository architecture and team context across four SDLC domains:
1. **Requirements & design** (`requirements_design`)
2. **Development** (`code_refactoring`)
3. **Testing** (`qa_testing`)
4. **Deployment & monitoring** (`devops_monitoring`)

---

## 1. Directory Structure

```text
SDLC-Compass/
├── backend/            # FastAPI backend and multi-agent diagnostic engine
├── frontend/           # Vue 3 + Vite + TypeScript application
├── frontend-legacy/    # Original vanilla prototype UI (preserved)
├── docs/               # Architecture guides and API contracts
└── tests/              # Backend pytest test suite
```

---

## 2. Running the Backend

### Prerequisites
- Python 3.10+ (tested on Python 3.12)
- Dependencies installed from `backend/requirements.txt`

```powershell
# From the SDLC-Compass directory:
cd SDLC-Compass
pip install -r backend/requirements.txt

# Start FastAPI uvicorn development server:
uvicorn backend.main:app --port 8000 --reload
```

The API will be available at `http://localhost:8000`. Interactive OpenAPI documentation is available at `http://localhost:8000/docs`.

---

## 3. Running Backend Tests

Run the test suite using `pytest`:

```powershell
# From the SDLC-Compass directory:
cd SDLC-Compass
pytest tests/test_api.py -v
```

---

## 4. Running the Frontend (Vue 3 + Vite)

### Prerequisites
- Node.js 18+ and npm

```powershell
# From the SDLC-Compass/frontend directory:
cd SDLC-Compass/frontend
npm install
npm run dev
```

The frontend runs locally at `http://localhost:5173`.

---

## 5. Switching Between Mocks and Real Backend

The frontend supports two operating modes configured in `SDLC-Compass/frontend/.env`:

### Mode A: Standalone Mock Mode (Default)
In this mode, the frontend operates completely offline using fixture data and in-memory mock responses:
```env
VITE_USE_MOCKS=true
VITE_API_URL=/api
```
Run frontend:
```powershell
cd SDLC-Compass/frontend
npm run dev
```

### Mode B: Connected Real Backend Mode
In this mode, the frontend sends live requests to the FastAPI backend at `http://localhost:8000`:
1. Start the FastAPI backend:
   ```powershell
   cd SDLC-Compass
   uvicorn backend.main:app --port 8000
   ```
2. Update `SDLC-Compass/frontend/.env`:
   ```env
   VITE_USE_MOCKS=false
   VITE_API_URL=/api
   ```
3. Start the frontend:
   ```powershell
   cd SDLC-Compass/frontend
   npm run dev
   ```
   *Note: Vite dev server automatically proxies `/api/*` to `http://localhost:8000/*`.*

---

## 6. PDF Report Export & WeasyPrint System Requirements

The application generates diagnostic reports deliverable via `GET /sessions/{session_id}/report/pdf`.

- **On Windows machines without GTK3**:
  WeasyPrint requires native C runtime libraries (`libgobject-2.0-0.dll`, `libpango-1.0-0.dll`, `libcairo-2.dll`).
  If these libraries are not present in your system `PATH`, WeasyPrint will report:
  `OSError: cannot load library 'libgobject-2.0-0': error 0x7e`
- **Graceful Fallback**:
  The backend automatically catches this exception and serves the generated consulting report as a styled standalone `.html` deliverable instead of failing.
- **To enable native PDF rendering on Windows**:
  Install the GTK3 runtime for Windows (e.g., via MSYS2 `pacman -S mingw-w64-x86_64-gtk3 mingw-w64-x86_64-pango`) or follow the [WeasyPrint Windows installation guide](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows).
