# Pathology DES — Simulation Lab

Discrete-event simulations of cytopathology and histopathology workflows, with a React UI and FastAPI backend that stores run artifacts in Google Cloud Storage (fake-gcs locally).

## Layout

```
backend/
  app/           FastAPI API (routes, schemas, GCS store, runner)
  models/        Callable run_cyto / run_histo
  utils/         Shared DES + analysis pipeline
  parameters/    YAML presets + JSON loader
shared/          cyto/histo default parameter JSON (API + UI source of truth)
frontend/        Vite + React two-pane UI
docker-compose.yml   fake-gcs-server
```

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker (for the GCS emulator)

## 1. Start the GCS emulator

```bash
docker compose up -d
```

This starts `fake-gcs-server` on `http://localhost:4443` and creates the `sim-results` bucket.

## 2. Backend API

```bash
python3 -m pip install -r requirements.txt
cd backend
export GCS_EMULATOR_HOST=http://localhost:4443
export GCS_BUCKET=sim-results
export GCS_PROJECT=local-dev
export PYTHONPATH=.
export MPLCONFIGDIR=/tmp/mpl
uvicorn app.main:app --reload --port 8000
```

Health check: [http://localhost:8000/api/health](http://localhost:8000/api/health)

### API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Liveness |
| `GET` | `/api/parameters/defaults/{cyto\|histo}` | Default parameter JSON |
| `POST` | `/api/simulations/run` | Run sim, upload artifacts, return URL map |
| `GET` | `/api/simulations/{run_id}` | Re-fetch artifact URLs |

Request body for `/run`:

```json
{
  "kind": "cyto",
  "seed": 42,
  "parameters": { "...": "full parameter object matching shared defaults" }
}
```

## 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

UI layout:

- **Left pane** — modality (cyto/histo), seed, Run, recent runs
- **Main top** — process pipeline + editable parameters
- **Main bottom** — analysis tables (CSV) and plots (PNG) loaded from artifact URLs

## CLI (no UI)

From `backend/`:

```bash
python v4.0_cytosim.py
python v2_histosim.py
```

Or as a library:

```python
from models.cyto import run_cyto
run_cyto(parameters_dict, seed=42)
```

## Production GCS

Unset the emulator and point at a real bucket:

```bash
unset GCS_EMULATOR_HOST
export GCS_BUCKET=your-prod-bucket
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa.json
```

Signed/public URL generation uses `https://storage.googleapis.com/...` when no emulator host is set.

## Deferred

- Username/password auth and saved user work (DB)
- Optional right-hand chatbot pane (layout reserved)
- Async multi-replication jobs
