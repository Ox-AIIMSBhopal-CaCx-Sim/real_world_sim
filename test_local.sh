#!/usr/bin/env bash
# Start the local development stack (GCS emulator + API + frontend).
# Usage (from repo root):
#   ./test_local.sh
# Optional:
#   BACKEND_ONLY=1 ./test_local.sh   # API + GCS only
#   FRONTEND_ONLY=1 ./test_local.sh  # Vite only (expects API already running)
#   SKIP_INSTALL=1 ./test_local.sh   # skip pip/npm install

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

GCS_EMULATOR_HOST="${GCS_EMULATOR_HOST:-http://localhost:4443}"
GCS_BUCKET="${GCS_BUCKET:-sim-results}"
GCS_PROJECT="${GCS_PROJECT:-local-dev}"
API_PORT="${API_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
VITE_API_BASE="${VITE_API_BASE:-http://localhost:${API_PORT}}"
SKIP_INSTALL="${SKIP_INSTALL:-0}"
BACKEND_ONLY="${BACKEND_ONLY:-0}"
FRONTEND_ONLY="${FRONTEND_ONLY:-0}"

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo
  echo "==> Stopping local servers…"
  if [[ -n "$FRONTEND_PID" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  wait 2>/dev/null || true
  echo "==> Done (GCS emulator left running — stop with: docker compose down)"
}
trap cleanup EXIT INT TERM

python_bin() {
  if [[ -x "$ROOT/.venv/bin/python" ]]; then
    echo "$ROOT/.venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    command -v python3
  else
    echo "error: python3 not found" >&2
    exit 1
  fi
}

wait_for_url() {
  local url="$1"
  local name="$2"
  local attempts="${3:-60}"
  local i
  for ((i = 1; i <= attempts; i++)); do
    if curl -sf "$url" >/dev/null 2>&1; then
      echo "==> $name is ready"
      return 0
    fi
    sleep 1
  done
  echo "error: timed out waiting for $name at $url" >&2
  return 1
}

start_gcs() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "error: docker not found (needed for fake-gcs-server)" >&2
    exit 1
  fi

  echo "==> Starting GCS emulator (docker compose)…"
  docker compose up -d

  echo "==> Waiting for GCS emulator on ${GCS_EMULATOR_HOST}…"
  # fake-gcs answers on /storage/v1/b
  local i
  for ((i = 1; i <= 60; i++)); do
    if curl -sf "${GCS_EMULATOR_HOST}/storage/v1/b" >/dev/null 2>&1; then
      echo "==> GCS emulator is ready"
      return 0
    fi
    sleep 1
  done
  echo "error: GCS emulator did not become ready on ${GCS_EMULATOR_HOST}" >&2
  echo "       Run: docker compose up -d && docker compose logs" >&2
  exit 1
}

ensure_backend_deps() {
  local py
  py="$(python_bin)"
  if [[ "$SKIP_INSTALL" == "1" ]]; then
    return 0
  fi
  echo "==> Ensuring Python deps ($py)…"
  "$py" -m pip install -q -r "$ROOT/requirements.txt"
}

ensure_frontend_deps() {
  if [[ "$SKIP_INSTALL" == "1" ]]; then
    return 0
  fi
  if [[ ! -d "$ROOT/frontend/node_modules" ]]; then
    echo "==> Installing frontend deps…"
    (cd "$ROOT/frontend" && npm install --no-audit --no-fund)
  fi
}

start_backend() {
  local py
  py="$(python_bin)"
  ensure_backend_deps

  if ! "$py" -c "import uvicorn" 2>/dev/null; then
    echo "error: uvicorn missing — activate .venv or: $py -m pip install -r requirements.txt" >&2
    exit 1
  fi

  echo "==> Starting API on http://localhost:${API_PORT}…"
  (
    cd "$ROOT/backend"
    export GCS_EMULATOR_HOST GCS_BUCKET GCS_PROJECT
    export PYTHONPATH=.
    export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/mpl}"
    export SIM_OUTPUT_ROOT="${SIM_OUTPUT_ROOT:-$ROOT/backend/sim_results}"
    exec "$py" -m uvicorn app.main:app --reload --host 127.0.0.1 --port "$API_PORT"
  ) &
  BACKEND_PID=$!

  wait_for_url "http://127.0.0.1:${API_PORT}/api/health" "API"
}

start_frontend() {
  ensure_frontend_deps

  echo "==> Starting frontend on http://localhost:${FRONTEND_PORT}…"
  (
    cd "$ROOT/frontend"
    export VITE_API_BASE
    exec npm run dev -- --host 127.0.0.1 --port "$FRONTEND_PORT"
  ) &
  FRONTEND_PID=$!

  # Vite may take a moment; don't fail hard if health isn't HTTP JSON
  sleep 2
  if curl -sf "http://127.0.0.1:${FRONTEND_PORT}/" >/dev/null 2>&1; then
    echo "==> Frontend is ready"
  else
    echo "==> Frontend starting (open http://localhost:${FRONTEND_PORT} shortly)…"
  fi
}

echo "==> Local test stack"
echo "    Repo:     $ROOT"
echo "    GCS:      $GCS_EMULATOR_HOST  bucket=$GCS_BUCKET"
echo "    API:      http://localhost:${API_PORT}"
echo "    UI:       http://localhost:${FRONTEND_PORT}"
echo

if [[ "$FRONTEND_ONLY" != "1" ]]; then
  start_gcs
  start_backend
fi

if [[ "$BACKEND_ONLY" != "1" ]]; then
  start_frontend
fi

echo
echo "==> Ready"
[[ "$FRONTEND_ONLY" != "1" ]] && echo "    Health:  http://localhost:${API_PORT}/api/health"
[[ "$BACKEND_ONLY" != "1" ]] && echo "    App:     http://localhost:${FRONTEND_PORT}"
echo "    Ctrl+C to stop the servers"
echo

# Keep script alive while children run
if [[ -n "$BACKEND_PID" && -n "$FRONTEND_PID" ]]; then
  wait "$BACKEND_PID" "$FRONTEND_PID"
elif [[ -n "$BACKEND_PID" ]]; then
  wait "$BACKEND_PID"
elif [[ -n "$FRONTEND_PID" ]]; then
  wait "$FRONTEND_PID"
fi
