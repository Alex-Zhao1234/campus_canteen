#!/bin/sh
# 容器启动：迁移到最新 → 幂等导入种子 → 起服务
set -e
echo "==> alembic upgrade head"
alembic upgrade head
if [ -f ../data/seed/dishes.csv ]; then
  echo "==> seed"
  python -m app.tasks.seed ../data/seed/dishes.csv
fi
echo "==> uvicorn"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'
