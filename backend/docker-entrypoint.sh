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
# Render 等平台通过 PORT 指定端口，compose 里用默认 8000
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips='*'
