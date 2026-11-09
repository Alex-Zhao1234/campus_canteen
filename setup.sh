#!/usr/bin/env bash
# 一键初始化开发环境（在 WSL / Linux 下运行）
set -e
cd "$(dirname "$0")"

echo "==> 检查工具"
command -v python3 >/dev/null || { echo "缺少 python3，请先: sudo apt install python3 python3-venv"; exit 1; }
command -v node >/dev/null    || { echo "缺少 node，请先安装 Node.js 20+（推荐 nvm）"; exit 1; }

echo "==> 后端：创建虚拟环境并安装依赖"
if command -v uv >/dev/null; then
  (cd backend && uv sync --extra dev)
else
  python3 -m venv backend/.venv
  backend/.venv/bin/pip install -q --upgrade pip
  backend/.venv/bin/pip install -q -e "backend[dev]"
fi

echo "==> 前端：安装依赖"
(cd frontend && npm install --silent)

echo "==> 初始化 .env 与数据目录"
[ -f .env ] || cp .env.example .env
mkdir -p data/images

echo
echo "完成。启动方式："
echo "  后端:  cd backend && source .venv/bin/activate && uvicorn app.main:app --reload"
echo "  前端:  cd frontend && npm run dev"
echo "  接口文档: http://localhost:8000/docs"
