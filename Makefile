.PHONY: setup dev-api dev-web test lint seed migrate migration

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
	cd backend && .venv/bin/python -m app.tasks.seed ../data/seed/dishes.csv

# 升级数据库到最新迁移
migrate:
	cd backend && .venv/bin/alembic upgrade head

# 根据模型变更生成新迁移：make migration m="add_xxx"
migration:
	cd backend && .venv/bin/alembic revision --autogenerate -m "$(m)"
