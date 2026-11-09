.PHONY: setup dev-api dev-web test lint seed

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
