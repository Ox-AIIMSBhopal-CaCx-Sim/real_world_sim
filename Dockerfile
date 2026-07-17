# ---- frontend ----
FROM node:22-bookworm-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
# Empty base → same-origin /api calls behind Cloud Run
ENV VITE_API_BASE=
RUN npm run build

# ---- runtime ----
FROM python:3.11-slim-bookworm
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY shared/ ./shared/
COPY --from=frontend /frontend/dist ./frontend/dist

ENV PYTHONPATH=/app/backend \
    STATIC_DIR=/app/frontend/dist \
    SIM_OUTPUT_ROOT=/tmp/sim_results \
    SIM_USERS_PATH=/tmp/users.json \
    MPLCONFIGDIR=/tmp/mpl \
    PORT=8080

WORKDIR /app/backend
EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
