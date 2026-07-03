# Build React frontend
FROM node:22-alpine AS frontend-build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./frontend/
RUN cd frontend && npm install
COPY frontend/ ./frontend/
COPY shared/ ./shared/
RUN cd frontend && npm run build

# FastAPI + static assets
FROM python:3.12-slim
WORKDIR /app

COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY shared/ ./shared/
COPY --from=frontend-build /app/frontend/dist ./static/

ENV PYTHONPATH=/app/backend
ENV PORT=8080

WORKDIR /app/backend
EXPOSE 8080
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
