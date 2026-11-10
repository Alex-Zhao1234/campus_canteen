#!/bin/sh
# 容器启动：迁移到最新 → 幂等导入种子 → 起服务
set -e
echo "==> alembic upgrade head"
alembic upgrade head
if [ -f ../data/seed/dishes.csv ]; then
  echo "==> seed"
  if [ -f ../data/seed/seats.csv ]; then
    python -m app.tasks.seed ../data/seed/dishes.csv ../data/seed/seats.csv
  else
    python -m app.tasks.seed ../data/seed/dishes.csv
  fi
fi
if [ "${SEED_DEMO_REVIEWS:-false}" = "true" ]; then
  echo "==> demo reviews"
  python -m app.tasks.demo
fi
echo "==> uvicorn"
# Render 等平台通过 PORT 指定端口，compose 里用默认 8000
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips='*'
