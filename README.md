# 校园食堂点评推荐系统

帮助学生发现食堂新菜品、避开踩雷窗口。架构设计见 `docs/架构设计.md`。

- 前端：React 18 + TypeScript + Vite
- 后端：Python 3.11+ / FastAPI / SQLAlchemy 2.0 (async)
- 数据库：SQLite（WAL），第二阶段加入 sqlite-vec 向量检索
- 项目介绍页（展示用，源码在 `docs/showcase/index.html`）：https://claude.ai/artifact/9oBEZPyiWA3QHYsiHH4mdt

## WSL 环境准备（首次）

在 WSL（Ubuntu）终端中：

```bash
# 1. 系统依赖
sudo apt update && sudo apt install -y python3 python3-venv python3-pip build-essential sqlite3 unzip

# 2. Node.js 20（推荐 nvm）
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
source ~/.bashrc
nvm install 20

# 3. （可选）uv —— 更快的 Python 包管理
curl -LsSf https://astral.sh/uv/install.sh | sh

# 4. Claude Code（在 WSL 内安装，不是 PowerShell）
curl -fsSL https://claude.ai/install.sh | bash
```

> 项目请放在 WSL 文件系统内（如 `~/projects/campus-canteen`），不要放在 `/mnt/c/` 下，否则文件监听和热更新会很慢。

## 初始化项目

```bash
mkdir -p ~/projects && cd ~/projects
unzip ~/campus-canteen.zip && cd campus-canteen
./setup.sh
git init && git add -A && git commit -m "init: 项目骨架"
```

## 日常开发

```bash
# 终端 1：后端
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload          # http://localhost:8000/docs

# 终端 2：前端
cd frontend && npm run dev             # http://localhost:5173

# 终端 3：Claude Code
claude
```

VS Code：安装 **WSL** 扩展，在 WSL 终端执行 `code .` 打开项目；推荐扩展已写在 `.vscode/extensions.json`。

## 目录

```
backend/   FastAPI 应用（app/ 下按 core / models / schemas / services / recommender / vector / api 分层）
frontend/  React 前端
data/      SQLite 文件、种子 CSV、图片
docs/      架构设计文档
CLAUDE.md  给 Claude Code 的项目上下文
```
