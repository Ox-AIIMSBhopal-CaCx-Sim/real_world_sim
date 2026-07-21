#!/usr/bin/env bash
#
# Run the app locally with hot reload — no image builds.
#   * FastAPI (uvicorn --reload)  on http://localhost:8000
#   * Vite dev server             on http://localhost:5173
#   * fake-gcs emulator (compose) on http://localhost:4443  (storage backend)
#
#   ./local-test.sh          # start both dev servers (Ctrl+C to stop)
#   ./local-test.sh --down   # stop the fake-gcs emulator
#
# Useful overrides:
#   SKIP_INSTALL=1   skip pip/npm dependency install
#   USE_EMULATOR=0   talk to the real GCS bucket instead of the emulator
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT_DIR}"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
EMULATOR_PORT="${EMULATOR_PORT:-4443}"
USE_EMULATOR="${USE_EMULATOR:-1}"

# ---- teardown ---------------------------------------------------------------
if [[ "${1:-}" == "--down" ]]; then
  echo "==> Stopping fake-gcs emulator"
  docker compose down
  exit 0
fi

# ---- storage backend --------------------------------------------------------
if [[ "${USE_EMULATOR}" == "1" ]]; then
  echo "==> Starting fake-gcs emulator (docker compose)"
  docker compose up -d
  export GCS_EMULATOR_HOST="http://localhost:${EMULATOR_PORT}"
  export GCS_BUCKET="${GCS_BUCKET:-sim-results}"
  export GCS_PROJECT="${GCS_PROJECT:-local-dev}"
else
  echo "==> Using real GCS bucket ${GCS_BUCKET:-pathology-simulation} (needs ADC creds)"
  unset GCS_EMULATOR_HOST || true
  export GCS_BUCKET="${GCS_BUCKET:-pathology-simulation}"
  export GCS_PROJECT="${GCS_PROJECT:-marine-shell-490317-u9}"
fi

# ---- python deps ------------------------------------------------------------
if [[ -d .venv ]]; then
  # shellcheck disable=SC1091
  set +u; source .venv/bin/activate; set -u
fi
if [[ "${SKIP_INSTALL:-0}" != "1" ]]; then
  echo "==> Installing Python dependencies"
  python3 -m pip install -q -r requirements.txt
fi

# ---- frontend deps ----------------------------------------------------------
if [[ "${SKIP_INSTALL:-0}" != "1" && ! -d frontend/node_modules ]]; then
  echo "==> Installing frontend dependencies"
  (cd frontend && npm install --no-audit --no-fund)
fi

# ---- run --------------------------------------------------------------------
export SIM_OUTPUT_ROOT="${SIM_OUTPUT_ROOT:-${ROOT_DIR}/backend/sim_results}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-${ROOT_DIR}/.mplcache}"
mkdir -p "${MPLCONFIGDIR}"

BACK_PID=""
FRONT_PID=""
cleanup() {
  echo ""
  echo "==> Shutting down dev servers"
  [[ -n "${FRONT_PID}" ]] && kill "${FRONT_PID}" 2>/dev/null || true
  [[ -n "${BACK_PID}" ]] && kill "${BACK_PID}" 2>/dev/null || true
  wait 2>/dev/null || true
  echo "    (emulator left running — stop it with ./local-test.sh --down)"
}
trap cleanup INT TERM EXIT

echo "==> Starting FastAPI on http://localhost:${BACKEND_PORT}"
( cd backend && PYTHONPATH=. exec uvicorn app.main:app --reload --port "${BACKEND_PORT}" ) &
BACK_PID=$!

echo "==> Starting Vite on http://localhost:${FRONTEND_PORT}"
( cd frontend && exec npm run dev -- --port "${FRONTEND_PORT}" ) &
FRONT_PID=$!

echo ""
echo "==> Ready:"
echo "    UI   http://localhost:${FRONTEND_PORT}"
echo "    API  http://localhost:${BACKEND_PORT}/api/health"
echo "    Ctrl+C to stop both servers."
echo ""

wait
