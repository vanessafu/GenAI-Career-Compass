FROM node:24-slim AS frontend

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_API_BASE_URL=
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HF_HUB_DISABLE_XET=1

WORKDIR /app
RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend ./backend
RUN uv sync --frozen --no-dev

COPY --from=frontend /app/frontend/dist ./frontend/dist

CMD ["sh", "-c", ".venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
