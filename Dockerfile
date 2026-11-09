# 单容器镜像（Render 等免费托管用）：前端构建产物由 FastAPI 一起托管。
# 本地开发与 docker-compose 仍用 backend/ 与 frontend/ 各自的 Dockerfile。

# 阶段 1：构建前端
FROM node:20-alpine AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# 阶段 2：后端 + 静态文件
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/backend/.venv \
    PATH="/app/backend/.venv/bin:$PATH" \
    STATIC_DIR=/app/static \
    DATABASE_URL=sqlite+aiosqlite:///../data/canteen.db

WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/ .
RUN uv sync --frozen --no-dev && chmod +x docker-entrypoint.sh

COPY --from=web /web/dist /app/static
COPY data/seed /app/data/seed

EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
