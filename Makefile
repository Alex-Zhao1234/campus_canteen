.PHONY: setup dev-api dev-web test lint seed rankings migrate migration up down logs

setup:
	./setup.sh

dev-api:
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

dev-web:
	cd frontend && npm run dev

test:
	cd backend && .venv/bin/pytest -q

lint:
	cd backend && .venv/bin/ruff check app tests

seed:
	cd backend && .venv/bin/python -m app.tasks.seed ../data/seed/dishes.csv ../data/seed/seats.csv

# 手动重算 stats 并生成榜单快照（服务运行时每 10 分钟自动跑）
rankings:
	cd backend && .venv/bin/python -m app.tasks.rankings

# 升级数据库到最新迁移
migrate:
	cd backend && .venv/bin/alembic upgrade head

# 根据模型变更生成新迁移：make migration m="add_xxx"
migration:
	cd backend && .venv/bin/alembic revision --autogenerate -m "$(m)"

# Docker：整套起停（需要 Docker Desktop 并开启 WSL 集成）
up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f
